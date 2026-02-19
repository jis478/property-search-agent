# Stack Research

**Domain:** LangGraph ReAct agent with Playwright MCP, LangFuse tracing, FastAPI SSE backend
**Researched:** 2026-02-19
**Confidence:** MEDIUM (training data cutoff August 2025; version pins should be validated against PyPI before use)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Runtime | 3.12 is the stable production release with the best async performance |
| langgraph | `>=0.2,<0.3` | Agent orchestration, ReAct loop | `create_react_agent` is the idiomatic entry point; `0.2.x` series is stable API |
| langchain-core | `>=0.3,<0.4` | Message types, tool protocol, runnables | Protocol layer langgraph depends on; use this not the full `langchain` package |
| langchain-openai | `>=0.2,<0.3` | OpenAI LLM integration (`ChatOpenAI`) | Handles tool-calling, streaming, retries |
| langchain-mcp-adapters | `>=0.1,<0.2` | Bridge: MCP tools → LangChain/LangGraph tools | Converts MCP server tool schemas into `BaseTool` instances |
| fastapi | `>=0.115,<0.116` | HTTP API framework + SSE streaming | Async-native; `StreamingResponse` with `text/event-stream` for SSE |
| uvicorn[standard] | `>=0.30,<0.32` | ASGI server | Standard production ASGI server; `[standard]` adds uvloop on Linux |
| langfuse | `>=2.0,<3.0` | LLM observability / tracing | `CallbackHandler` integrates with LangGraph without touching graph internals |
| openai | `>=1.30,<2.0` | OpenAI Python SDK (transitive dep) | Pin to v1 until langchain-openai explicitly supports v2 |
| @playwright/mcp (npm) | latest | Playwright MCP server process | Microsoft's official Playwright MCP server; Node.js subprocess |
| Node.js | 20.x LTS | Runtime for @playwright/mcp | Required for the MCP server subprocess only |

### How the Packages Connect

```
User Request (HTTP POST)
        │
        ▼
FastAPI endpoint (async)
        │ creates
        ▼
LangGraph ReAct agent (create_react_agent)
        │ uses tools from
        ▼
langchain-mcp-adapters (MultiServerMCPClient)
        │ manages subprocess
        ▼
@playwright/mcp (Node.js process, stdio transport)
        │ controls
        ▼
Chromium → domain.com.au

Observability: LangGraph agent ──[CallbackHandler]──► LangFuse
Streaming:     agent.astream_events ──► FastAPI SSE ──► Browser EventSource
```

### LangFuse Integration (CallbackHandler)

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
)

result = await agent.ainvoke(
    {"messages": [("human", query)]},
    config={"callbacks": [langfuse_handler]},
)
```

### langchain-mcp-adapters: Bridge Pattern

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

async with MultiServerMCPClient({
    "playwright": {
        "command": "npx",
        "args": ["@playwright/mcp"],
        "transport": "stdio",
    }
}) as mcp_client:
    tools = await mcp_client.get_tools()
    agent = create_react_agent(model, tools)
```

**Critical:** Pre-warm the MCP client at FastAPI startup — do NOT create per request. Subprocess cold start is ~2-3 seconds.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `langchain` full package | Deprecated agents, hundreds of unused deps | `langchain-core` + `langchain-openai` only |
| `AgentExecutor` | Deprecated in favour of LangGraph | `langgraph.prebuilt.create_react_agent` |
| `playwright` Python lib directly | Cannot expose tools via MCP protocol | `@playwright/mcp` Node server |
| WebSockets for streaming | SSE is sufficient for unidirectional streaming | FastAPI `StreamingResponse` + browser `EventSource` |
| `gpt-4-turbo` / `gpt-3.5-turbo` | GPT-4o is faster, cheaper, better tool-calling | `gpt-4o` |
| `openai>=2.0` | Breaking changes; langchain-openai may not support | Pin `openai>=1.30,<2.0` |
