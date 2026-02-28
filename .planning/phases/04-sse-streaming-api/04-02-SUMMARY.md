---
phase: 04-sse-streaming-api
plan: "02"
subsystem: api
tags: [fastapi, cors, sse, asyncio, langgraph, testing, pytest]

# Dependency graph
requires:
  - phase: 04-sse-streaming-api
    plan: "01"
    provides: api/search.py POST /search router, api/stream.py GET /stream/{run_id} router, run_store dict, asyncio.Queue pipeline
  - phase: 03-langgraph-agent
    provides: build_agent, BotDetectedError/StepLimitError/MCPError exceptions
provides:
  - main.py with CORSMiddleware, build_agent lifespan call, search_router + stream_router inclusion
  - Unit tests for POST /search (4 tests) and GET /stream/{run_id} (3 tests)
  - Full runnable FastAPI app with SSE streaming endpoints wired and tested
affects:
  - 04-03-PLAN (end-to-end SSE tests — depends on this main.py integration)
  - 05-frontend (imports from fully wired app)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "mock_agent fixture: monkeypatch main.build_agent to prevent OpenAI API key requirement in tests"
    - "lifespan build_agent pattern: app.state.agent = build_agent(tools) immediately after MCP startup"
    - "run_store isolation: autouse fixture clears search_module.run_store and _current_run_id between tests"
    - "asyncio.Queue pre-population: create loop, put items, close loop before TestClient to inject SSE events in tests"

key-files:
  created:
    - tests/test_api_search.py
    - tests/test_api_stream.py
  modified:
    - main.py
    - tests/test_main.py

key-decisions:
  - "mock_agent fixture added to test_main.py (auto-fix): main.py lifespan now calls build_agent which requires OpenAI API key; existing tests regressed without mock"
  - "stream=True kwarg dropped from TestClient.get(): httpx TestClient does not support stream kwarg on .get(); full response body works for SSE content-type and body assertions"
  - "CORSMiddleware registered with allow_origins=['*'], GET+POST methods, SSE-specific headers (Content-Type, Cache-Control, X-Accel-Buffering)"

patterns-established:
  - "Agent lifespan: app.state.agent set during startup so request handlers access via request.app.state.agent"
  - "Test isolation: autouse fixture clears module-level run_store dict and _current_run_id before/after each test"

requirements-completed: [API-01, API-02, API-03, API-04, API-05]

# Metrics
duration: 8min
completed: 2026-03-01
---

# Phase 4 Plan 02: main.py Integration and API Unit Tests Summary

**CORSMiddleware, build_agent lifespan wiring, and router inclusion in main.py with 7 new unit tests covering 202/409/422 responses and SSE content-type/event emission**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-28T20:40:25Z
- **Completed:** 2026-03-01T00:00:00Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 modified, 2 created)

## Accomplishments

- `main.py` updated with CORSMiddleware (allow_origins=["*"]), `build_agent(tools)` call in lifespan storing agent at `app.state.agent`, and both API routers included via `app.include_router`
- `tests/test_api_search.py` with 4 tests: 202 run_id response, run created in store, 409 when run active, 422 on missing query
- `tests/test_api_stream.py` with 3 tests: 404 for unknown run_id, SSE Content-Type header, event emitted then stream closes on sentinel
- Full test suite passes: 46 tests (39 pre-existing + 7 new), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Update main.py** - `b7494da` (feat) — CORSMiddleware, build_agent lifespan, router inclusion + test_main.py auto-fix
2. **Task 2: Write unit tests** - `73acc54` (feat) — test_api_search.py and test_api_stream.py

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `main.py` — Added CORSMiddleware import and registration, `from agent import build_agent`, `from api.search/stream import router`, `app.state.agent = build_agent(tools)` in lifespan, `app.include_router(search_router)`, `app.include_router(stream_router)`
- `tests/test_main.py` — Added `mock_agent` fixture and applied to all 4 existing test functions (auto-fix)
- `tests/test_api_search.py` — New: 4 tests for POST /search endpoint behavior
- `tests/test_api_stream.py` — New: 3 tests for GET /stream/{run_id} SSE endpoint behavior

## Decisions Made

- `mock_agent` fixture added to `test_main.py` to prevent OpenAI API key requirement — lifespan now calls `build_agent` which instantiates `ChatOpenAI`, requiring `OPENAI_API_KEY`; patching `main.build_agent` avoids this in all existing tests
- `stream=True` kwarg dropped from `TestClient.get()` — httpx's `TestClient` does not accept this parameter; the content-type assertion works without it since TestClient buffers the full response

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added mock_agent fixture to test_main.py to fix regression**
- **Found during:** Task 1 verification (existing test_main.py tests run after main.py update)
- **Issue:** main.py lifespan now calls `build_agent(tools)` which internally creates `ChatOpenAI(model="gpt-4o")` requiring `OPENAI_API_KEY` environment variable; all 4 existing tests in test_main.py failed with `openai.OpenAIError: The api_key client option must be set`
- **Fix:** Added `mock_agent` fixture to test_main.py that monkeypatches `main.build_agent` to return a `MagicMock`, applied to all 4 existing test functions
- **Files modified:** tests/test_main.py
- **Verification:** All 4 tests in test_main.py pass after fix
- **Committed in:** b7494da (Task 1 commit)

**2. [Rule 1 - Bug] Removed unsupported stream=True kwarg from TestClient.get()**
- **Found during:** Task 2 (first test run of test_api_stream.py)
- **Issue:** Plan included `client.get(f"/stream/{run_id}", stream=True)` but `TestClient.get()` does not accept a `stream` keyword argument; raised `TypeError`
- **Fix:** Dropped `stream=True` kwarg; TestClient buffers full response body so content-type and body assertions work without it
- **Files modified:** tests/test_api_stream.py
- **Verification:** test_stream_sse_content_type passes; SSE Content-Type header present in response
- **Committed in:** 73acc54 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs — regression from plan integration + incorrect API usage)
**Impact on plan:** Both fixes necessary for tests to pass. No scope creep. All 7 planned tests implemented and passing.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FastAPI app is fully wired: CORSMiddleware, agent built in lifespan, both SSE routers mounted
- Plan 03 (end-to-end SSE tests) can proceed — the integration tested here is the foundation it depends on
- `app.state.agent` is available to request handlers via `request.app.state.agent` as planned

---
*Phase: 04-sse-streaming-api*
*Completed: 2026-03-01*
