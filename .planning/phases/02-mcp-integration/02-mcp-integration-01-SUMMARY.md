---
phase: 02-mcp-integration
plan: 01
subsystem: infra
tags: [playwright-mcp, langchain-mcp-adapters, fastapi, subprocess, mcp, asyncio, chromium]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "FastAPI skeleton with lifespan context manager, mcp/ stub package"
provides:
  - "MCPManager class in mcp_subprocess/manager.py with start(), stop(), crash-detection, auto-restart"
  - "FastAPI lifespan wired to MCPManager.start() with hard-fail on RuntimeError"
  - "GET /health returns {status, mcp} fields — MCP-aware health endpoint"
  - "GET /tools returns {count, tools: [{name, description}]} — 22 browser tools available"
  - "Chromium auto-installation via npx playwright install chromium at first startup"
  - "langchain-mcp-adapters>=0.2.1,<0.3 in requirements.txt"
  - "mcp_subprocess/ package (renamed from mcp/ to avoid SDK name conflict)"
affects:
  - 03-agent
  - 04-streaming-api
  - 05-ui

# Tech tracking
tech-stack:
  added:
    - "langchain-mcp-adapters==0.2.1"
    - "mcp==1.26.0 (langchain-mcp-adapters transitive)"
    - "langchain-core==1.2.14 (langchain-mcp-adapters transitive)"
    - "@playwright/mcp 0.0.68 (npm, spawned via npx)"
    - "Playwright Chromium 1208 (downloaded via npx playwright install chromium)"
  patterns:
    - "MCPManager._make_client() uses MultiServerMCPClient with persistent session() context manager"
    - "MCP startup: asyncio.wait_for(session_cm.__aenter__(), timeout=5.0) — hard-fail on timeout"
    - "MCP shutdown: session_cm.__aexit__() closes stdin, pkill -9 chromium fallback after 2s"
    - "FastAPI lifespan hard-fail: raise before yield causes server to refuse startup with non-zero exit"
    - "app.state.mcp_manager and app.state.mcp_tools set at startup, used by /health and /tools routes"
    - "crash detection: asyncio.TimeoutError/BrokenPipeError/ConnectionResetError trigger _restart() task"
    - "mcp_subprocess/ package name (not mcp/) avoids shadowing Anthropic mcp SDK in sys.path"

key-files:
  created:
    - mcp_subprocess/manager.py
    - mcp_subprocess/__init__.py
  modified:
    - main.py
    - requirements.txt

key-decisions:
  - "Renamed mcp/ to mcp_subprocess/ — local mcp/ package shadows installed mcp SDK (Anthropic), causing ImportError in langchain_mcp_adapters"
  - "MCPManager.start() uses persistent client.session('playwright') context manager — not get_tools() which spawns a subprocess per call"
  - "Chromium auto-install at startup: _ensure_chromium() checks ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome — runs npx playwright install chromium if missing"
  - "pkill -9 chromium fallback in stop() after 2s: MCP session.__aexit__() closes stdin but Chromium children may linger"
  - "Crash counter resets on successful restart — gives 3 attempts per crash event for resilience"
  - "jinja2 not installed in rental-search conda env — installed as Rule 3 fix (pre-existing env gap)"

patterns-established:
  - "request.app.state.mcp_manager — Phase 3 agent accesses MCPManager via app.state"
  - "request.app.state.mcp_tools — Phase 3 agent accesses tool list via app.state"
  - "Hard-fail lifespan: never catch-and-swallow RuntimeError from manager.start() — let it propagate"
  - "All MCP subprocess logic in mcp_subprocess/manager.py, not inlined into main.py"

requirements-completed: [SCRP-01]

# Metrics
duration: 30min
completed: 2026-02-20
---

# Phase 2 Plan 01: MCP Integration Summary

**MCPManager class wires @playwright/mcp Node.js subprocess into FastAPI lifespan with persistent ClientSession, 22 browser tools loaded at startup, hard-fail on startup error, crash-restart up to 3x, and zombie-free Chromium shutdown**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-02-20T07:02:33Z
- **Completed:** 2026-02-20T07:35:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- MCPManager class in mcp_subprocess/manager.py with full lifecycle: start, stop, crash detection, auto-restart
- FastAPI /health returns `{"status":"ok","mcp":"ready"}` — confirmed live with running server
- FastAPI /tools returns 22 browser tools (`browser_navigate`, `browser_click`, `browser_snapshot`, etc.) — confirmed live
- Clean shutdown: zero Chromium zombie processes after `kill` — verified with `ps aux | grep chromium`
- Auto-downloads Chromium on first startup (detected missing ~100MB, downloaded via `npx playwright install chromium`)

## Task Commits

Each task was committed atomically:

1. **Task 1: MCPManager class and requirements update** - `9e48563` (feat)
2. **Task 2: Wire MCPManager into FastAPI lifespan, /health, /tools** - `8ee068f` (feat)

**Plan metadata:** (committed after summary — see final docs commit)

## Files Created/Modified
- `/home/mark/hobby/mcp_subprocess/manager.py` - MCPManager class: start(), stop(), _restart(), call_with_crash_detection(), tools/ready properties, _ensure_chromium(), _force_kill_chromium()
- `/home/mark/hobby/mcp_subprocess/__init__.py` - Package exporting MCPManager (renamed from mcp/)
- `/home/mark/hobby/main.py` - Updated lifespan + MCP-aware /health + new /tools endpoint
- `/home/mark/hobby/requirements.txt` - Added langchain-mcp-adapters>=0.2.1,<0.3

## Decisions Made
- Renamed `mcp/` package to `mcp_subprocess/` to avoid shadowing the Anthropic `mcp` SDK — Python's sys.path prepends `''` (cwd), so a local `mcp/` directory takes precedence over the installed `mcp` package, causing `ImportError: cannot import name 'ClientSession' from 'mcp'` in langchain_mcp_adapters
- Used persistent `client.session("playwright")` context manager held in lifespan — not `client.get_tools()` per request (which spawns a new subprocess each call)
- Chromium auto-install at startup: checks `~/.cache/ms-playwright/chromium-*/chrome-linux/chrome` glob, runs `npx playwright install chromium` if missing
- Crash restart counter resets on successful restart — allows 3 attempts per crash event, not lifetime-capped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed mcp/ package to mcp_subprocess/ to resolve name conflict with Anthropic mcp SDK**
- **Found during:** Task 1 (import verification step)
- **Issue:** `from langchain_mcp_adapters.tools import load_mcp_tools` raised `ImportError: cannot import name 'ClientSession' from 'mcp' (/home/mark/hobby/mcp/__init__.py)`. Python's sys.path puts `''` (project root) first, so the local `mcp/` stub shadows the installed `mcp` SDK package.
- **Fix:** Renamed project directory `mcp/` to `mcp_subprocess/`, updated `mcp_subprocess/__init__.py`, and updated `main.py` import to `from mcp_subprocess.manager import MCPManager`. Confirmed `from mcp import ClientSession` (SDK) imports correctly after rename.
- **Files modified:** mcp_subprocess/__init__.py, mcp_subprocess/manager.py (new), main.py
- **Verification:** `python3 -c "from langchain_mcp_adapters.client import MultiServerMCPClient; print('OK')"` passes; `/health` and `/tools` endpoints verified live
- **Committed in:** `9e48563` (Task 1 commit), `8ee068f` (Task 2 commit)

**2. [Rule 3 - Blocking] Installed missing jinja2 in rental-search conda env**
- **Found during:** Integration verification (server startup)
- **Issue:** Server crashed on startup: `AssertionError: jinja2 must be installed to use Jinja2Templates`. The `rental-search` conda env did not have jinja2 installed (it was in requirements.txt but the env was not created by installing from requirements.txt).
- **Fix:** Ran `/home/mark/miniconda3/envs/rental-search/bin/pip install "jinja2>=3.1,<4"`. Installed jinja2==3.1.6.
- **Files modified:** None (environment-only fix)
- **Verification:** Server started successfully, `/health` returned 200
- **Committed in:** Environment-only fix, not in source commits

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary — mcp/ rename is essential for the package to function; jinja2 install is a pre-existing env gap. No scope creep.

## Issues Encountered
- The plan used `mcp/manager.py` as the output path throughout. The rename to `mcp_subprocess/` is a permanent change — Phase 3 and later plans must import from `mcp_subprocess.manager` not `mcp.manager`.
- The `python3` command in the system (`/usr/bin/python3`) is system Python 3.12.3 without pip or any installed packages. All Python must run via `/home/mark/miniconda3/envs/rental-search/bin/python3` (Python 3.11.14) or the `uvicorn` binary in that env.

## User Setup Required
None — Chromium is auto-downloaded on first server startup.

## Next Phase Readiness
- MCPManager is running and Phase 3 (LangGraph agent) can access it via `request.app.state.mcp_manager`
- All 22 browser tools available via `app.state.mcp_tools` — Phase 3 can pass these directly to the LangGraph ReAct agent
- Phase 3 plans should import from `mcp_subprocess.manager` (not `mcp.manager`)
- Phase 3 should add `call_with_crash_detection()` wrapping around all tool calls to the MCP subprocess

## Self-Check: PASSED

All created files verified present on disk:
- FOUND: mcp_subprocess/manager.py
- FOUND: mcp_subprocess/__init__.py
- FOUND: main.py
- FOUND: requirements.txt
- FOUND: 02-mcp-integration-01-SUMMARY.md

All task commits verified in git log:
- FOUND: 9e48563 (Task 1 feat)
- FOUND: 8ee068f (Task 2 feat)
