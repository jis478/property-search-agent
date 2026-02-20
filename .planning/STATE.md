# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Agent autonomously navigates domain.com.au and returns structured property listings — browser automation must work reliably and results must appear in the UI
**Current focus:** Phase 2 — MCP Integration (complete, both plans done)

## Current Position

Phase: 2 of 5 (MCP Integration)
Plan: 2 of 2 in current phase
Status: Phase 2 complete — ready for Phase 3
Last activity: 2026-02-20 — Phase 2 Plan 02 completed

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 14 min
- Total execution time: 0.70 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 1 | 10 min | 10 min |
| 02-mcp-integration | 2 | 32 min | 16 min |

**Recent Trend:**
- Last 5 plans: 14 min avg
- Trend: stable (Plan 02 was fast at 2 min — hermetic test suite)

*Updated after each plan completion*

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: domain.com.au URL params and JSON-LD availability need empirical validation before/during Phase 3 planning
- [Phase 3]: playwright-stealth compatibility with @playwright/mcp subprocess is unconfirmed
- [Phase 3]: LLM reliability for Australian suburb-to-postcode+path mapping is unproven
- [All phases]: mcp_subprocess/ package (not mcp/) — all future phases must import from mcp_subprocess.manager

## Session Continuity

Last session: 2026-02-20
Stopped at: Completed 02-mcp-integration-02-PLAN.md — Phase 2 fully complete (both plans done), ready for Phase 3
Resume file: None
