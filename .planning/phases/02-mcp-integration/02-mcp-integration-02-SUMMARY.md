---
phase: 02-mcp-integration
plan: 02
subsystem: testing
tags: [pytest, pytest-asyncio, fastapi, mcp, mock, monkeypatch, asyncio]

# Dependency graph
requires:
  - phase: 02-mcp-integration
    plan: 01
    provides: "MCPManager class in mcp_subprocess/manager.py, FastAPI lifespan wired to MCPManager, /health and /tools endpoints"
provides:
  - "tests/test_main.py with mock_mcp fixture patching main.MCPManager — 4 tests covering /health (ok+degraded), /tools, and index"
  - "tests/test_mcp.py with 4 async unit tests for MCPManager: timeout raises, exception raises, start sets ready, stop clears ready"
  - "pytest.ini with asyncio_mode = auto for hermetic async test execution"
  - "pytest-asyncio>=0.24 in requirements-dev.txt"
affects:
  - 03-agent
  - 04-streaming-api
  - 05-ui

# Tech tracking
tech-stack:
  added:
    - "pytest-asyncio==0.26.0"
  patterns:
    - "monkeypatch.setattr('main.MCPManager', lambda: mock_manager) — patches at import site in main.py, not at definition"
    - "AsyncMock for start()/stop() on mock_manager — lifespan awaits these without spawning subprocess"
    - "patch.object(manager, '_ensure_chromium', new=AsyncMock()) — prevents filesystem/subprocess calls in MCPManager unit tests"
    - "patch('mcp_subprocess.manager.MCP_STARTUP_TIMEOUT', 0.05) — fast timeout for timeout-raises test (50ms vs 5s)"
    - "pytest.ini asyncio_mode = auto — all async test functions run as asyncio coroutines without explicit mark"

key-files:
  created:
    - tests/test_mcp.py
    - pytest.ini
  modified:
    - tests/test_main.py
    - requirements-dev.txt

key-decisions:
  - "Patch at main.MCPManager (not mcp_subprocess.manager.MCPManager) — monkeypatch must replace the name at the import site used by lifespan"
  - "Patch MCP_STARTUP_TIMEOUT to 0.05s in timeout test — avoids 5-second wait while still exercising timeout branch"
  - "Patch _ensure_chromium as AsyncMock in unit tests — prevents filesystem glob and subprocess calls unrelated to the test subject"
  - "Use mcp_subprocess.manager import path throughout (not mcp.manager) — reflects permanent rename from Phase 2 Plan 01"

patterns-established:
  - "All test_main.py tests use mock_mcp fixture — prevents test suite hanging if MCPManager is ever made async"
  - "MCP unit tests patch at mcp_subprocess.manager.* namespace — consistent with package rename"
  - "TestClient(app) used as context manager — triggers lifespan startup/shutdown in test"

requirements-completed: [SCRP-01]

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 2 Plan 02: MCP Integration Test Suite Summary

**Hermetic pytest suite for MCP-aware FastAPI: mock_mcp fixture prevents subprocess spawn, 8 tests cover /health degraded state, /tools shape, and MCPManager timeout/exception/ready lifecycle — all pass in 1.18s**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-20T07:15:24Z
- **Completed:** 2026-02-20T07:17:04Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- mock_mcp pytest fixture patches `main.MCPManager` so lifespan never spawns a real Node.js subprocess
- test_health_ok and test_health_degraded assert the new `{status, mcp}` response shape from /health
- test_tools_endpoint verifies `{count, tools: [{name, description}]}` shape with named tools
- 4 async MCPManager unit tests verify timeout raises RuntimeError, exception raises RuntimeError, ready=True after start, ready=False after stop
- Full suite: 8 passed in 1.18s — no subprocess spawned, no filesystem access, CI-safe

## Task Commits

Each task was committed atomically:

1. **Task 1: Update test_main.py with MCPManager mock fixture** - `e1434c8` (feat)
2. **Task 2: Add MCPManager unit tests in test_mcp.py** - `17f8403` (feat)

**Plan metadata:** (committed after summary — see final docs commit)

## Files Created/Modified
- `/home/mark/hobby/tests/test_main.py` - Rewrote with mock_mcp fixture; 4 tests: test_health_ok, test_health_degraded, test_tools_endpoint, test_index_returns_html
- `/home/mark/hobby/tests/test_mcp.py` - New: 4 async unit tests for MCPManager lifecycle
- `/home/mark/hobby/pytest.ini` - New: asyncio_mode = auto for pytest-asyncio
- `/home/mark/hobby/requirements-dev.txt` - Added pytest-asyncio>=0.24,<1

## Decisions Made
- Patched `main.MCPManager` (not `mcp_subprocess.manager.MCPManager`) — monkeypatch must replace the name at the call site used by lifespan (`manager = MCPManager()` in `main.py`)
- Used `patch('mcp_subprocess.manager.MCP_STARTUP_TIMEOUT', 0.05)` to make the timeout test fast (50ms vs the real 5s)
- Patched `_ensure_chromium` as `AsyncMock()` in all MCPManager unit tests — prevents filesystem globs and subprocess calls that are unrelated to each test's concern
- Used `mcp_subprocess.manager` import path throughout test_mcp.py, reflecting the permanent rename from Plan 01

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected import path in test_mcp.py from mcp.manager to mcp_subprocess.manager**
- **Found during:** Task 2 (writing test_mcp.py)
- **Issue:** Plan specified `from mcp.manager import MCPManager` and `patch("mcp.manager.load_mcp_tools", ...)` but the actual package was renamed to `mcp_subprocess/` in Plan 01 to avoid shadowing the Anthropic MCP SDK
- **Fix:** Used `from mcp_subprocess.manager import MCPManager` and `patch("mcp_subprocess.manager.load_mcp_tools", ...)` throughout
- **Files modified:** tests/test_mcp.py
- **Verification:** 4 async tests passed; `python3 -c "from mcp_subprocess.manager import MCPManager; print('OK')"` succeeds
- **Committed in:** `17f8403` (Task 2 commit)

**2. [Rule 1 - Bug] Added _ensure_chromium patch and reduced MCP_STARTUP_TIMEOUT in unit tests**
- **Found during:** Task 2 (designing test_start_raises_on_timeout)
- **Issue:** Plan's test for timeout used `asyncio.sleep(10)` which would wait 5 real seconds (MCP_STARTUP_TIMEOUT). `_ensure_chromium()` was also unpatched, which would attempt filesystem operations in CI
- **Fix:** Patched `MCP_STARTUP_TIMEOUT` to 0.05s and patched `_ensure_chromium` as `AsyncMock()` in all MCPManager unit tests
- **Files modified:** tests/test_mcp.py
- **Verification:** Timeout test passes in <0.1s; full suite completes in 0.48s
- **Committed in:** `17f8403` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs — incorrect import paths, missing mocks for correctness/speed)
**Impact on plan:** Both fixes necessary for tests to pass in CI. No scope creep.

## Issues Encountered
- pytest and httpx were not installed in the `rental-search` conda env (requirements-dev.txt existed but env was not bootstrapped from it). Installed via pip as part of Task 1 verification — env gap, not a code issue.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Test suite is CI-ready: all 8 tests pass in 1.18s, no subprocess spawned, no Node.js required
- Phase 3 (LangGraph agent) should follow the same mock_mcp pattern when testing endpoints that use `request.app.state.mcp_manager`
- Phase 3 tests can extend the mock_mcp fixture with `mock_mcp.call_with_crash_detection = AsyncMock(side_effect=...)` to test crash-detection behavior

---
*Phase: 02-mcp-integration*
*Completed: 2026-02-20*

## Self-Check: PASSED

All created files verified present on disk:
- FOUND: tests/test_main.py
- FOUND: tests/test_mcp.py
- FOUND: pytest.ini
- FOUND: requirements-dev.txt
- FOUND: 02-mcp-integration-02-SUMMARY.md

All task commits verified in git log:
- FOUND: e1434c8 (Task 1 feat — test_main.py with mock_mcp fixture)
- FOUND: 17f8403 (Task 2 feat — test_mcp.py, pytest.ini, requirements-dev.txt)
