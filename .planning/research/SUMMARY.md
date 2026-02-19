# Project Research Summary

**Project:** LangGraph ReAct Property Search Agent
**Domain:** Natural-language property search over domain.com.au via LangGraph + Playwright MCP + FastAPI SSE + LangFuse
**Researched:** 2026-02-19
**Confidence:** MEDIUM

## Executive Summary

This project is a single-user local development tool that accepts natural-language property search queries, uses a LangGraph ReAct agent to browse domain.com.au via a Playwright-controlled browser, and streams results back to the user in real time via Server-Sent Events. The recommended architecture is a two-process Python/Node.js application: FastAPI (with LangGraph and langchain-mcp-adapters) as the primary process, and a Playwright MCP server (`@playwright/mcp`) as a long-lived Node.js subprocess. The agent constructs domain.com.au search URLs directly from LLM-extracted parameters rather than interacting with the search form — this is the most reliable scraping strategy and the central architectural decision.

The key risks are all infrastructure rather than algorithmic. Bot detection by domain.com.au's Cloudflare protection is the single highest-uncertainty risk. The Playwright MCP subprocess lifecycle must be implemented correctly from day one or accumulated zombie Chromium processes will destabilise the server. LangGraph's default recursion limit of 25 must be lowered to prevent runaway LLM loops when the agent encounters bot-blocked pages.

---

## Key Findings

### Stack

| Technology | Version | Role |
|------------|---------|------|
| Python | 3.12.x | Runtime |
| langgraph | `>=0.2,<0.3` | Agent orchestration (`create_react_agent`) |
| langchain-core | `>=0.3,<0.4` | Message types, tool protocol |
| langchain-openai | `>=0.2,<0.3` | GPT-4o integration |
| langchain-mcp-adapters | `>=0.1,<0.2` | MCP → LangChain tool bridge |
| fastapi | `>=0.115,<0.116` | HTTP API + SSE streaming |
| uvicorn[standard] | `>=0.30,<0.32` | ASGI server |
| langfuse | `>=2.0,<3.0` | LLM observability (`CallbackHandler`) |
| openai | `>=1.30,<2.0` | Pin to v1 (langchain-openai may not support v2) |
| @playwright/mcp (npm) | latest | Browser automation via MCP (Node.js subprocess) |
| Node.js | 20.x LTS | Runtime for @playwright/mcp only |

**Critical:** Use `langchain-core` + `langchain-openai` only — not the full `langchain` package. Use `create_react_agent` — not deprecated `AgentExecutor`.

### Table Stakes Features

- Natural-language query input + submit
- Live SSE streaming of agent steps (without this, 15-30s wait feels broken)
- Structured listing cards (address, price, beds, baths, property type, listing URL)
- LLM parameter extraction + domain.com.au URL construction
- Plain-English step display showing URL being navigated to
- Error state (bot detection, timeout) and zero-results state
- Interpretation feedback ("Searching: 3 beds, Fitzroy VIC, $600k-$800k")

**domain.com.au URL structure:**
```
https://www.domain.com.au/{intent}/{suburb}-{state}-{postcode}/
  ?bedrooms={min}-{max}&price={min}-{max}&propertyTypes={type}
```
Construct URLs directly — skip the search form entirely.

**Suburb mapping** (e.g. "Fitzroy" → `fitzroy-vic-3065`) is the most failure-prone step — needs a validation spike.

### Architecture

Two-process application:
- **Process 1:** Python — FastAPI + LangGraph + MCP client
- **Process 2:** Node.js — `@playwright/mcp` subprocess (stdio pipe, JSON-RPC 2.0)

**Two-step SSE pattern** (required because `EventSource` only supports GET):
- `POST /search` → stores query, returns `run_id`
- `GET /stream/{run_id}` → SSE stream via `StreamingResponse`

**LangFuse:** New `CallbackHandler(session_id=run_id)` per request — never shared.

**Build order:**
```
Phase 1: Foundation (FastAPI skeleton, config, .gitignore)
Phase 2: MCP Integration (subprocess lifecycle — highest risk, validate early)
Phase 3: LangGraph Agent without streaming (verify correctness first)
Phase 4: FastAPI SSE Streaming (add after agent is proven)
Phase 5: LangFuse Observability (one-line addition to working stream)
Phase 6: Frontend Wiring (depends on stable SSE API contract)
```

### Watch Out For

1. **MCP subprocess not cleaned up** — `try/finally` in FastAPI `lifespan`; process group kill for Chromium children. **Phase 1.**
2. **LangGraph infinite loop** — Set `recursion_limit: 10` in every `astream_events()` call; catch `GraphRecursionError`. **Phase 2.**
3. **Playwright bot detection** — Validate page title/content before returning to agent; `playwright-stealth`; randomized delays. **Phase 3.**
4. **SSE stream stays open on disconnect** — Poll `request.is_disconnected()` in generator; 120s hard timeout. **Phase 4.**
5. **CSS selector brittleness** — Never use generated class names (`css-1a2b3c`). Use `data-testid`, ARIA roles, JSON-LD. **Phase 3.**
6. **LangFuse orphaned traces** — Pass `CallbackHandler` per-invocation in `config={"callbacks": [...]}`, not globally. **Phase 5.**
7. **Blocking Playwright in async** — Only `from playwright.async_api` — never `sync_api`. **Phase 2/3.**
8. **API key leakage** — `.gitignore` + `pydantic-settings` before any keys are created. **Phase 1.**
9. **CORS blocks EventSource** — Add `CORSMiddleware`; test from browser (not curl). **Phase 4.**
10. **LangGraph state not JSON serializable** — Use `astream_events()` not `astream()`; validate every SSE event type round-trips via `json.loads()`. **Phase 4.**

---

## Implications for Roadmap

6 phases, mapping directly to the dependency chain and pitfall-to-phase mapping:

| Phase | Name | Goal | Key Risk Addressed |
|-------|------|------|--------------------|
| 1 | Foundation | FastAPI serves index.html, config, git setup | API key leakage, MCP lifecycle pattern |
| 2 | MCP Integration | Playwright MCP subprocess spawns at startup, tools load | Subprocess lifecycle, blocking async |
| 3 | LangGraph Agent | Agent browses domain.com.au, returns listings (no streaming) | Bot detection, selector strategy, recursion limit |
| 4 | SSE Streaming | Streaming endpoint emits agent events to terminal | Disconnect leak, CORS, state serialization |
| 5 | LangFuse | Full trace visible in LangFuse dashboard | Context propagation, orphaned spans |
| 6 | Frontend | End-to-end: type query → see stream → see cards | Frontend depends on stable SSE contract |

### Research Flags for Planning

- **Phase 3 needs a scraping spike first:** domain.com.au URL structure (verify live), JSON-LD availability on search results pages, `playwright-stealth` + `@playwright/mcp` compatibility, suburb-to-URL mapping reliability
- **Phase 4:** Verify actual `astream_events(version="v2")` event names (`on_chat_model_stream`, `on_tool_start`, `on_tool_end`) against installed package
- **Phases 1, 5, 6:** Standard patterns, skip dedicated research phase

---

## Confidence Assessment

| Area | Confidence | Key Uncertainty |
|------|------------|-----------------|
| Stack | MEDIUM | `langchain-mcp-adapters` API surface (new library); verify PyPI versions |
| Features | MEDIUM | domain.com.au URL params — verify against live site |
| Architecture | MEDIUM | `MultiServerMCPClient` config params — verify against current docs |
| Pitfalls | MEDIUM | Bot detection mitigation effectiveness — needs empirical testing |

**Gaps to validate before/during Phase 3:**
- domain.com.au live URL format and query parameter names
- JSON-LD availability on search results pages (vs. listing detail pages only)
- `playwright-stealth` compatibility with `@playwright/mcp` Node.js subprocess
- LLM reliability for Australian suburb → postcode + path mapping

---

*Research completed: 2026-02-19 | Ready for roadmap: yes*
