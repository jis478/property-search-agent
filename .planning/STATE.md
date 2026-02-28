# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Agent autonomously navigates domain.com.au and returns structured property listings — browser automation must work reliably and results must appear in the UI
**Current focus:** Phase 4 — SSE Streaming API (in progress)

## Current Position

Phase: 4 of 5 (SSE Streaming API)
Plan: 2 of 3 in current phase (Plans 01 and 02 complete)
Status: Phase 4 in progress — Plans 01 and 02 done (route modules + main.py integration + unit tests); Plan 03 pending
Last activity: 2026-03-01 — Phase 4 Plan 02 completed (main.py CORS/agent/router wiring; test_api_search.py + test_api_stream.py; 46 tests passing)

Progress: [████████░░] 77%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 8 min
- Total execution time: 0.78 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 1 | 10 min | 10 min |
| 02-mcp-integration | 2 | 32 min | 16 min |
| 03-langgraph-agent (partial) | 3 | 6 min | 2 min |

**Recent Trend:**
- Last 5 plans: 8 min avg
- Trend: Phase 3 plans fast (infrastructure + wiring — no new tests required)

*Updated after each plan completion*
| Phase 03-langgraph-agent P04 | ~30 min | 2 tasks | 3 files |
| Phase 04-sse-streaming-api P01 | 2 min | 2 tasks | 2 files |
| Phase 04-sse-streaming-api P02 | 8 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: LangGraph ReAct agent with GPT-4o — standard tool-using agent pattern
- [Init]: Playwright MCP as subprocess — browser control via MCP protocol
- [Init]: FastAPI + SSE — no WebSocket complexity, native browser support
- [Init]: URL construction (not form interaction) — most reliable scraping strategy
- [01-01]: Path(__file__).parent for Jinja2Templates — prevents TemplateNotFound from non-root uvicorn start
- [01-01]: TestClient as context manager — required for Phase 2 lifespan state correctness
- [01-01]: python3.12-venv unavailable without sudo — bootstrapped pip via get-pip.py (Python 3.12.3 confirmed)
- [02-01]: mcp/ renamed to mcp_subprocess/ — local mcp/ shadows Anthropic mcp SDK, causing ImportError in langchain_mcp_adapters
- [02-01]: Persistent client.session('playwright') in lifespan — not get_tools() per request (spawns new subprocess each call)
- [02-01]: Chromium auto-install at startup — checks ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome glob
- [02-01]: Crash restart counter resets on successful restart — 3 attempts per crash event, not lifetime-capped
- [Phase 02-mcp-integration]: Patch at main.MCPManager (not mcp_subprocess.manager.MCPManager) — monkeypatch replaces name at lifespan call site
- [Phase 02-mcp-integration]: Patch MCP_STARTUP_TIMEOUT to 0.05s in timeout test — fast without removing timeout branch coverage
- [Phase 03-02]: langgraph 1.0.10 installed (>=1.0.9 satisfied); openai upgraded 2.17.0->2.24.0 as transitive dep
- [Phase 03-02]: SYSTEM_PROMPT explicitly restricts to 3 tools only; bot_detected flag in JSON output enables typed BotDetectedError raising in parser
- [Phase 03-langgraph-agent]: Deferred import of BotDetectedError inside parse_listings_from_message body — avoids ImportError when Plan 02 not yet committed
- [Phase 03-langgraph-agent]: Partial-results contract: bot_detected=True + non-empty listings returns data (not raises) — per CONTEXT.md locked decision
- [Phase 03-langgraph-agent]: price field is str|None (not float) — preserves display format like dollar-450-pw or Price-on-application
- [Phase 03-03]: recursion_limit=15 passed via config dict at ainvoke time (RunnableConfig field) — create_react_agent in langgraph 1.0.10 does not accept it as constructor param
- [Phase 03-03]: Tool filtering at build_agent using REQUIRED_TOOLS set — only 3 of ~22 Playwright MCP tools admitted
- [Phase 03-04]: --browser chromium flag added to MCPManager subprocess args — WSL2 does not have Google Chrome; @playwright/mcp defaults to Chrome and fails silently; --browser chromium forces use of the playwright-managed Chromium binary
- [Phase 03-04]: pre_model_hook added to build_agent — OpenAI API rejects images in role:tool messages; langchain-mcp-adapters places browser_take_screenshot results in ToolMessages; hook lifts image content to preceding HumanMessage before each LLM call
- [Phase 04-01]: run_store imported by reference in api/stream.py from api.search — both modules share same dict instance without shared state layer
- [Phase 04-01]: _final_text accumulated from on_chat_model_stream chunks — only way to get agent's final JSON output from astream_events v2 (no on_agent_finish event)
- [Phase 04-01]: partial flag derived from bot_detected JSON field before parse_listings_from_message call — best-effort parse, stays False on failure
- [Phase 04-01]: asyncio.wait_for(timeout=15) for keep-alive pings — prevents queue.get() blocking indefinitely without a separate ping task
- [Phase 04-sse-streaming-api]: mock_agent fixture required in all test_main.py tests: lifespan now calls build_agent which creates ChatOpenAI requiring OPENAI_API_KEY; monkeypatching main.build_agent prevents regression
- [Phase 04-sse-streaming-api]: TestClient.get() does not accept stream=True kwarg; dropped from test_api_stream.py — buffered response sufficient for SSE content-type and body assertions

### Pending Todos

None yet.

### Blockers/Concerns

- [All phases]: mcp_subprocess/ package (not mcp/) — all future phases must import from mcp_subprocess.manager
- [Phase 4+]: OpenAI API rejects images in role:tool messages — pre_model_hook in build_agent handles this; Phase 4 inherits fix automatically
- [Phase 4+]: WSL2 requires --browser chromium in MCPManager — already hardcoded; no action needed

**Resolved (Phase 3 empirical validation):**
- domain.com.au URL params confirmed working — 17 listings returned in smoke test
- playwright-stealth not needed — domain.com.au did not trigger bot challenge
- LLM suburb-to-URL mapping confirmed reliable for Richmond VIC query

## Session Continuity

Last session: 2026-03-01
Stopped at: Completed 04-sse-streaming-api-02-PLAN.md — main.py updated with CORSMiddleware, build_agent lifespan, router inclusion; test_api_search.py and test_api_stream.py created; all 46 tests pass; ready for Plan 03 (end-to-end SSE tests)
Resume file: None
