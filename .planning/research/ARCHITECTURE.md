# Architecture Research

**Domain:** LangGraph ReAct agent with Playwright MCP server + FastAPI backend
**Researched:** 2026-02-19
**Confidence:** MEDIUM (training knowledge August 2025; verify package API surface before implementing)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser (Client)                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Single HTML page                                            │   │
│  │  - Text input for natural-language query                     │   │
│  │  - SSE listener: renders agent step stream in real-time      │   │
│  │  - Listing card renderer: shows results after completion     │   │
│  └────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────│─────────────────────────────────────┘
                                │ HTTP POST /search
                                │ GET /stream/{run_id}  (SSE)
┌───────────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Process (single Python process)            │
│                                                                       │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐   │
│  │   POST /search       │    │   GET /stream/{run_id}           │   │
│  │   - Validates input  │    │   - StreamingResponse            │   │
│  │   - Stores query     │    │   - async generator yields       │   │
│  │   - Returns run_id   │    │     SSE-formatted chunks         │   │
│  └──────────┬───────────┘    └──────────────────────────────────┘   │
│             │                                                         │
│  ┌──────────▼──────────────────────────────────────────────────┐    │
│  │                    Agent Runner                               │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │  LangGraph ReAct Agent (compiled StateGraph)         │    │    │
│  │  │  - Node: LLM (GPT-4o via ChatOpenAI)                │    │    │
│  │  │  - Node: ToolNode (MCP tools via                    │    │    │
│  │  │          langchain-mcp-adapters)                     │    │    │
│  │  │  - .astream_events() yields event stream            │    │    │
│  │  └─────────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │  LangFuse CallbackHandler                            │    │    │
│  │  │  - Attached as LangChain callback per request       │    │    │
│  │  │  - Traces: LLM calls, tool invocations, latency     │    │    │
│  │  └─────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│             │                                                         │
│  ┌──────────▼──────────────────────────────────────────────────┐    │
│  │  MCP Client (MultiServerMCPClient / StdioConnection)         │    │
│  │  - Created at app startup (lifespan)                        │    │
│  │  - Connects to Playwright MCP subprocess via stdio pipe     │    │
│  │  - Loads tool list → converted to LangChain BaseTool        │    │
│  └──────────┬───────────────────────────────────────────────────┘   │
└─────────────│───────────────────────────────────────────────────────┘
              │ stdio (stdin/stdout pipe)  JSON-RPC 2.0 / MCP protocol
┌─────────────▼───────────────────────────────────────────────────────┐
│  Playwright MCP Server Process  (Node.js subprocess)                 │
│  npx @playwright/mcp@latest                                          │
│  - Spawned at FastAPI startup, killed at shutdown                    │
│  - Exposes Playwright browser tools: navigate, click, fill, extract  │
│  - Browser: Chromium, headless by default                            │
└─────────────────────────────────────────────────────────────────────┘
              │ Chromium browser
              ▼
        domain.com.au
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| Browser (HTML) | User input, SSE rendering, listing cards | Vanilla JS EventSource, no build step |
| FastAPI router | HTTP endpoints: POST /search, GET /stream/{id} | `StreamingResponse` with async generator |
| Agent Runner | Orchestrates LangGraph, yields SSE events | `graph.astream_events()` in async context |
| LangGraph StateGraph | ReAct loop: LLM ↔ ToolNode cycle | `create_react_agent` prebuilt |
| ToolNode | Executes MCP tool calls returned by LLM | LangGraph `ToolNode` + langchain-mcp-adapters tools |
| MCP Client | Manages Playwright subprocess, exposes tools | `MultiServerMCPClient` |
| Playwright MCP subprocess | Runs Chromium, exposes browser actions as MCP tools | `npx @playwright/mcp --headless` via stdio |
| LangFuse callback | Traces every LLM call and tool invocation | `langfuse.callback.CallbackHandler` per request |

---

## Process Model

**Two-process application:**

```
Process 1: Python (uvicorn + FastAPI + LangGraph + MCP client)
Process 2: Node.js (Playwright MCP server — child of Process 1)
```

- Communication via stdio pipe (stdin/stdout), JSON-RPC 2.0 over MCP protocol
- MCP client in Python writes to subprocess stdin, reads from stdout
- Subprocess spawned at FastAPI startup, killed at shutdown
- One browser instance for the lifetime of the server (single-user tool)

---

## MCP Server Lifecycle

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client: MultiServerMCPClient | None = None
mcp_tools: list = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_client, mcp_tools
    mcp_client = MultiServerMCPClient({
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--headless"],
            "transport": "stdio",
        }
    })
    await mcp_client.__aenter__()
    mcp_tools = await mcp_client.get_tools()
    yield
    await mcp_client.__aexit__(None, None, None)

app = FastAPI(lifespan=lifespan)
```

**Note:** Verify `MultiServerMCPClient` parameter names against current `langchain-mcp-adapters` docs.

---

## SSE Streaming Architecture

```python
async def agent_event_stream(query: str) -> AsyncGenerator[str, None]:
    langfuse_handler = CallbackHandler(session_id=run_id)

    async for event in graph.astream_events(
        {"messages": [HumanMessage(content=query)]},
        version="v2",
        config={"callbacks": [langfuse_handler]},
    ):
        event_type = event["event"]

        if event_type == "on_chat_model_stream":
            chunk = event["data"]["chunk"].content
            if chunk:
                yield f"data: {json.dumps({'type': 'thinking', 'content': chunk})}\n\n"

        elif event_type == "on_tool_start":
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': event['name']})}\n\n"

        elif event_type == "on_tool_end":
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': event['name']})}\n\n"

        elif event_type == "on_chain_end" and event.get("name") == "LangGraph":
            final = event["data"]["output"]
            last_msg = final["messages"][-1].content
            yield f"data: {json.dumps({'type': 'complete', 'result': last_msg})}\n\n"

    yield "data: [DONE]\n\n"
```

**Two-step SSE pattern (POST then GET):** The `EventSource` browser API only supports GET. Solution: POST `/search` stores the query and returns a `run_id`; GET `/stream/{run_id}` opens the SSE stream.

---

## Project Directory Structure

```
property-agent/
├── main.py                  # FastAPI app, lifespan, mounts static/
├── config.py                # pydantic-settings Settings class
├── agent/
│   ├── graph.py             # create_react_agent, system prompt
│   └── runner.py            # agent_event_stream() async generator
├── mcp/
│   └── client.py            # MCP client globals, init/teardown helpers
├── api/
│   ├── models.py            # SearchRequest, SearchResponse Pydantic models
│   └── routes.py            # POST /search, GET /stream/{run_id}
├── static/
│   └── index.html           # Single-page frontend (served by FastAPI)
├── .env                     # API keys (not committed)
├── .env.example             # Template for .env
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Configuration Management

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = "https://cloud.langfuse.com"
    playwright_headless: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Data Flow: Full Request Lifecycle

```
1. User types query → POST /search { "query": "3 bed house in Bondi under 2M" }
2. FastAPI: validate, store query, return { "run_id": "abc-123" }
3. Browser: EventSource opens GET /stream/abc-123
4. FastAPI: StreamingResponse(agent_event_stream(query), media_type="text/event-stream")
5. agent_event_stream() starts:
   - Creates LangFuse CallbackHandler(session_id=run_id)
   - Calls graph.astream_events({"messages": [HumanMessage(query)]}, version="v2")
6. LangGraph ReAct loop:
   a. GPT-4o receives system prompt + query
      → LangFuse traces LLM call
      → LLM decides: call playwright_navigate tool
   b. ToolNode: executes playwright_navigate("https://www.domain.com.au/...")
      → MCP client sends JSON-RPC to Playwright subprocess stdin
      → Playwright navigates Chromium to domain.com.au
      → Returns page content via stdout
      → LangFuse traces tool call
   c. GPT-4o sees result, decides next action (scroll, extract, etc.)
   d. Repeat until LLM produces final AIMessage with structured listings
7. agent_event_stream() yields SSE events throughout:
   - on_chat_model_stream → { type: "thinking", content: "..." }
   - on_tool_start        → { type: "tool_call", tool: "playwright_navigate" }
   - on_tool_end          → { type: "tool_result", tool: "playwright_navigate" }
   - on_chain_end (final) → { type: "complete", result: {...listings...} }
8. Browser EventSource renders: thinking stream → tool badges → listing cards
9. LangFuse (async): flushes trace — full timeline, token costs, tool latencies visible in UI
```

---

## Build Order

```
Phase 1: Foundation
  config.py (Settings)               ← no deps
  main.py skeleton (FastAPI)         ← needs config.py
  static/index.html (basic HTML)     ← no deps
  → Deliverable: curl localhost:8000 serves index.html

Phase 2: MCP Integration
  mcp/client.py (MultiServerMCPClient lifecycle)
  lifespan hook in main.py
  Verify: log tool list at startup
  → Deliverable: app starts, Playwright MCP subprocess spawns, tools load

Phase 3: LangGraph Agent (no streaming yet)
  agent/graph.py (create_react_agent with MCP tools)
  agent/runner.py (simple await graph.ainvoke())
  Test with hardcoded query, print result
  → Deliverable: agent browses domain.com.au, returns listings

Phase 4: FastAPI API + SSE Streaming
  api/models.py, api/routes.py
  agent/runner.py → astream_events() generator
  → Deliverable: curl /stream/abc shows SSE events in terminal

Phase 5: LangFuse Tracing
  CallbackHandler in agent/runner.py
  → Deliverable: LangFuse dashboard shows full trace

Phase 6: Frontend Wiring
  index.html: EventSource, step log, listing cards
  → Deliverable: end-to-end — type query, see stream, see cards
```

**Why this order:** MCP integration is highest risk (subprocess lifecycle) — validate early. LangGraph without streaming is simpler to debug. SSE added after agent correctness proven. LangFuse is a single-line addition. Frontend is last (depends on stable SSE API).

---

## Architectural Patterns

### Pattern 1: Lifespan-Managed MCP Subprocess
Use FastAPI `lifespan` to spawn/kill the Playwright subprocess. MCP client and tools stored as module-level globals. One instance, one browser, for the app lifetime. Simple, predictable.

### Pattern 2: Two-Step SSE (POST then GET)
`EventSource` only supports GET — POST `/search` stores query + returns `run_id`; GET `/stream/{run_id}` streams. Keeps query out of URL logs.

### Pattern 3: Per-Request LangFuse CallbackHandler
New `CallbackHandler` with unique `session_id` per request. Never share one handler across concurrent requests — traces would mix.

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Spawn MCP subprocess per request | 2-5s cold start per request | Spawn once in lifespan startup |
| `subprocess.run()` for MCP server | Blocks asyncio event loop | Use `asyncio.create_subprocess_exec()` (langchain-mcp-adapters handles this) |
| Global mutable query store without cleanup | Memory leak | `del query_store[run_id]` after stream completes |
| One MCP client for concurrent requests | Concurrent agents corrupt shared browser state | Accept serial requests for single-user tool |
| `except Exception: pass` around `astream_events` | Silent errors, browser sees `[DONE]` with no results | Catch specific exceptions, yield `{type: "error", message: "..."}` SSE event |

---

## Integration Points

| Service | Integration | Notes |
|---------|-------------|-------|
| OpenAI GPT-4o | `ChatOpenAI(model="gpt-4o")` | API key from env |
| Playwright MCP | stdio subprocess via `MultiServerMCPClient` | Managed by FastAPI lifespan |
| LangFuse | `CallbackHandler` per request | `session_id = run_id` for trace isolation |
| domain.com.au | Via Playwright browser (no direct HTTP) | Real browser — Playwright handles JS-rendered pages |

---

*Architecture research for: LangGraph ReAct agent + Playwright MCP + FastAPI + LangFuse*
*Researched: 2026-02-19*
