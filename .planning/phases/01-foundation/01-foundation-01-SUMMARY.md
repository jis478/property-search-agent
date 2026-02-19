---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [fastapi, uvicorn, pydantic-settings, jinja2, pytest, httpx, python]

# Dependency graph
requires: []
provides:
  - "Runnable FastAPI app (main.py) serving GET / and GET /health"
  - "pydantic-settings config singleton (config.py) loading from .env"
  - "Jinja2 HTML template shell with Tailwind CDN (templates/index.html)"
  - "Stub Python packages: agent/, api/, mcp/"
  - "Test suite: 2 passing pytest tests"
  - "Git hygiene: .gitignore, .env.example with all future API keys stubbed"
  - "README with complete setup, run, and test instructions"
affects:
  - 02-mcp-integration
  - 03-agent
  - 04-streaming-api
  - 05-ui

# Tech tracking
tech-stack:
  added:
    - "fastapi==0.129.0"
    - "uvicorn==0.41.0 (with standard extras: uvloop, websockets, watchfiles)"
    - "pydantic-settings==2.13.0"
    - "jinja2==3.1.6"
    - "pytest==9.0.2"
    - "httpx==0.28.1"
    - "starlette==0.52.1 (fastapi transitive)"
    - "python-dotenv==1.2.1 (pydantic-settings transitive)"
  patterns:
    - "TemplateResponse(request, name) — request-first signature (not legacy dict style)"
    - "Jinja2Templates(directory=Path(__file__).parent / 'templates') — absolute path prevents TemplateNotFound"
    - "TestClient used as context manager (with TestClient(app) as client:) — triggers lifespan"
    - "from pydantic_settings import BaseSettings (underscore, not hyphen in import)"
    - "settings = Settings() module-level singleton in config.py"

key-files:
  created:
    - main.py
    - config.py
    - templates/index.html
    - requirements.txt
    - requirements-dev.txt
    - .env.example
    - .gitignore
    - tests/test_main.py
    - README.md
    - agent/__init__.py
    - api/__init__.py
    - mcp/__init__.py
    - tests/__init__.py
  modified: []

key-decisions:
  - "Used Path(__file__).parent for Jinja2Templates directory — prevents TemplateNotFound when uvicorn starts from non-project-root"
  - "TestClient used as context manager — ensures lifespan startup/shutdown runs in tests (required for Phase 2 MCP state)"
  - "python3.12-venv unavailable without sudo — used python3 -m venv --without-pip + get-pip.py bootstrap successfully"
  - "pip install -r requirements-dev.txt installs httpx==0.28.1 (upper bound in spec is <0.29) — within range"

patterns-established:
  - "TemplateResponse(request, 'index.html') — Phase 4/5 must use this signature"
  - "TestClient as context manager — all future tests must follow this pattern"
  - "from config import settings — all future modules import the singleton this way"
  - "requirements.txt + requirements-dev.txt split — runtime vs dev deps always separate"

requirements-completed: [FRNT-01]

# Metrics
duration: 10min
completed: 2026-02-19
---

# Phase 1 Plan 01: Foundation Summary

**FastAPI skeleton with pydantic-settings config, Jinja2 HTML shell with Tailwind CDN, 2 passing pytest tests, and full git hygiene — verified server starts cleanly on Python 3.12.3**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-19T07:10:38Z
- **Completed:** 2026-02-19T07:20:00Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments
- Runnable FastAPI server at http://localhost:8000 — GET /health returns `{"status":"ok"}`, GET / returns 200 text/html
- pydantic-settings Settings singleton loading from .env with all future API keys stubbed (OpenAI, Langfuse)
- 2 passing pytest tests using TestClient as context manager (future-proof for Phase 2 lifespan state)
- Git hygiene established: .env gitignored, .env.example tracked with all required keys

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold** - `11e0ffc` (chore)
2. **Task 2: Python source files** - `025de08` (feat)
3. **Task 3: Tests, README, verification** - `bf7c9bf` (feat)

## Files Created/Modified
- `/home/mark/hobby/main.py` - FastAPI app with lifespan, GET /health, GET / routes
- `/home/mark/hobby/config.py` - pydantic-settings Settings singleton loading from .env
- `/home/mark/hobby/templates/index.html` - Bare HTML shell with Tailwind CDN (cdn.tailwindcss.com)
- `/home/mark/hobby/requirements.txt` - Runtime: fastapi, uvicorn[standard], pydantic-settings, jinja2
- `/home/mark/hobby/requirements-dev.txt` - Dev: pytest, httpx (extends requirements.txt)
- `/home/mark/hobby/.env.example` - Stubs: OPENAI_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
- `/home/mark/hobby/.gitignore` - Excludes .env, __pycache__, venv dirs, IDE files
- `/home/mark/hobby/tests/test_main.py` - 2 tests: test_health, test_index_returns_html
- `/home/mark/hobby/README.md` - Setup, run, test instructions and project structure
- `/home/mark/hobby/agent/__init__.py` - Stub package (Phase 3)
- `/home/mark/hobby/api/__init__.py` - Stub package (Phase 4)
- `/home/mark/hobby/mcp/__init__.py` - Stub package (Phase 2)
- `/home/mark/hobby/tests/__init__.py` - Empty package marker

## Exact Versions Installed (pip freeze, runtime deps only)

```
fastapi==0.129.0
uvicorn==0.41.0
pydantic-settings==2.13.0
Jinja2==3.1.6
starlette==0.52.1
pydantic==2.12.5
pydantic_core==2.41.5
python-dotenv==1.2.1  # pydantic-settings transitive dep
uvloop==0.22.1         # uvicorn[standard] extra
watchfiles==1.1.1      # uvicorn[standard] extra
websockets==16.0       # uvicorn[standard] extra
```

Dev extras: `pytest==9.0.2`, `httpx==0.28.1`

## Decisions Made
- `Path(__file__).parent / "templates"` for Jinja2Templates — absolute path prevents TemplateNotFound errors when uvicorn is started from a non-project-root directory
- TestClient used as context manager — ensures lifespan events fire in tests; required by Phase 2 which adds MCP subprocess state in lifespan
- python3.12-venv package unavailable without sudo — worked around by using `python3 -m venv --without-pip` + bootstrap pip via `get-pip.py`. Python 3.12.3 is confirmed available as `python3.12`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] python3.12-venv not available, bootstrapped pip manually**
- **Found during:** Task 3 (virtualenv verification step)
- **Issue:** `python3.12 -m venv .venv-verify` failed — python3-venv package not installed and sudo not available
- **Fix:** Used `python3 -m venv --without-pip` (creates venv structure without pip), then bootstrapped pip via `curl https://bootstrap.pypa.io/get-pip.py | python3`. This is equivalent to the plan's `python3.12 -m venv .venv-verify`.
- **Files modified:** None (environment-only fix, no source changes)
- **Verification:** `pip install -r requirements-dev.txt` succeeded, `pytest` reported `2 passed`
- **Committed in:** `bf7c9bf` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Workaround is equivalent — same Python 3.12.3, same pip, same packages. No scope creep.

## Issues Encountered
- `curl -I http://localhost:8000/` sends a HEAD request; FastAPI returns 405 because the route is GET-only. This is correct FastAPI behaviour — HEAD is not the same as GET. Verified with `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` which returned 200. The plan's verification step used `-I` illustratively; GET / works correctly.

## User Setup Required
None — no external service configuration required in Phase 1.

## Next Phase Readiness
- Server starts cleanly: `uvicorn main:app --reload` prints "Application startup complete"
- All packages installed and tests pass
- Phase 2 can safely add MCP subprocess lifecycle to the `lifespan` context manager in main.py
- Phase 2 should add MCP client/server logic in `mcp/__init__.py`
- All API keys stubbed in .env.example — developer only needs to add OPENAI_API_KEY before Phase 3

## Self-Check: PASSED

All created files verified present on disk:
- FOUND: main.py, config.py, templates/index.html, requirements.txt, requirements-dev.txt
- FOUND: .env.example, .gitignore, tests/test_main.py, README.md
- FOUND: agent/__init__.py, api/__init__.py, mcp/__init__.py, tests/__init__.py

All task commits verified in git log:
- FOUND: 11e0ffc (Task 1 chore)
- FOUND: 025de08 (Task 2 feat)
- FOUND: bf7c9bf (Task 3 feat)

---
*Phase: 01-foundation*
*Completed: 2026-02-19*
