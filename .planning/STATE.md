# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Agent autonomously navigates domain.com.au and returns structured property listings — browser automation must work reliably and results must appear in the UI
**Current focus:** Phase 3 — LangGraph Agent (in progress)

## Current Position

Phase: 3 of 5 (LangGraph Agent)
Plan: 3 of 4 in current phase (Plans 01, 02, and 03 complete)
Status: Phase 3 in progress — Plans 01, 02, and 03 done, Plan 04 remaining
Last activity: 2026-02-28 — Phase 3 Plan 03 completed

Progress: [██████░░░░] 60%

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
| Phase 03-langgraph-agent P04 | 2 | 1 tasks | 1 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: domain.com.au URL params and JSON-LD availability need empirical validation before/during Phase 3 planning
- [Phase 3]: playwright-stealth compatibility with @playwright/mcp subprocess is unconfirmed
- [Phase 3]: LLM reliability for Australian suburb-to-postcode+path mapping is unproven
- [All phases]: mcp_subprocess/ package (not mcp/) — all future phases must import from mcp_subprocess.manager

## Session Continuity

Last session: 2026-02-28
Stopped at: Completed 03-langgraph-agent-03-PLAN.md — property_agent.py with build_agent + search_properties, agent/__init__.py public API
Resume file: None
