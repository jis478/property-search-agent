---
phase: 01-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - requirements-dev.txt
  - .env.example
  - .gitignore
  - config.py
  - main.py
  - templates/index.html
  - agent/__init__.py
  - api/__init__.py
  - mcp/__init__.py
  - tests/__init__.py
  - tests/test_main.py
  - README.md
autonomous: true
requirements:
  - FRNT-01

must_haves:
  truths:
    - "GET / returns 200 with Content-Type: text/html"
    - "GET /health returns {\"status\": \"ok\"}"
    - "uvicorn main:app starts without errors or warnings"
    - "pytest passes with 2 tests (health + index)"
    - "pip install -r requirements.txt succeeds in a fresh virtualenv"
    - "API keys are loaded from environment variables — no secrets hardcoded in source"
    - ".env is excluded from git; .env.example is tracked"
  artifacts:
    - path: "main.py"
      provides: "FastAPI app, lifespan, GET / and GET /health routes"
      exports: ["app"]
    - path: "config.py"
      provides: "Settings singleton loaded from .env"
      exports: ["settings"]
    - path: "templates/index.html"
      provides: "Bare HTML shell with Tailwind CDN"
      contains: "cdn.tailwindcss.com"
    - path: "requirements.txt"
      provides: "Runtime dependencies with compatible version ranges"
    - path: "requirements-dev.txt"
      provides: "Dev dependencies (pytest, httpx)"
    - path: ".gitignore"
      provides: "Excludes .env, __pycache__, virtualenv dirs"
    - path: ".env.example"
      provides: "All future keys stubbed with placeholder values"
    - path: "tests/test_main.py"
      provides: "Tests for health and index endpoints"
  key_links:
    - from: "main.py"
      to: "templates/index.html"
      via: "Jinja2Templates(directory=Path(__file__).parent / 'templates')"
      pattern: "Jinja2Templates"
    - from: "main.py"
      to: "config.py"
      via: "from config import settings"
      pattern: "from config import settings"
    - from: "tests/test_main.py"
      to: "main.py"
      via: "from main import app"
      pattern: "from main import app"
---

<objective>
Create the FastAPI project skeleton for the Property Search Agent: dependency files, config management, bare HTML shell, stub packages, tests, git hygiene, and README. The server must start cleanly and pass tests before any subsequent phase can build on it.

Purpose: Establish a verified, runnable base. Every later phase assumes this phase is complete and correct.
Output: A runnable FastAPI app at http://localhost:8000 with passing tests and a clean git setup.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation/01-CONTEXT.md
@.planning/phases/01-foundation/RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Project scaffold — directories, dependency files, git hygiene, .env.example</name>
  <files>
    requirements.txt
    requirements-dev.txt
    .env.example
    .gitignore
  </files>
  <action>
Run the following commands from /home/mark/hobby to create the directory structure and write each file:

```bash
mkdir -p /home/mark/hobby/templates
mkdir -p /home/mark/hobby/agent
mkdir -p /home/mark/hobby/api
mkdir -p /home/mark/hobby/mcp
mkdir -p /home/mark/hobby/tests
```

Create /home/mark/hobby/requirements.txt with this exact content:
```
fastapi>=0.115,<0.130
uvicorn[standard]>=0.30,<0.42
pydantic-settings>=2.5,<3
jinja2>=3.1,<4
```

Create /home/mark/hobby/requirements-dev.txt with this exact content:
```
-r requirements.txt
pytest>=8.0,<10
httpx>=0.27,<0.29
```

Create /home/mark/hobby/.env.example with this exact content:
```
# Copy this file to .env and fill in your values.
# Do NOT commit .env to git.

# Required for Phase 3+ (LangGraph agent):
OPENAI_API_KEY=sk-...

# Required for Phase 4+ (observability via Langfuse, optional):
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Create /home/mark/hobby/.gitignore with this exact content:
```
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
.venv/
venv/
env/
.env/

# Environment / secrets — NEVER commit .env
.env
*.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# OS
.DS_Store
Thumbs.db
```

Note: python-dotenv is intentionally absent from requirements.txt — pydantic-settings installs it as a hard dependency automatically. Do NOT add it.
  </action>
  <verify>
```bash
cat /home/mark/hobby/requirements.txt
cat /home/mark/hobby/requirements-dev.txt
cat /home/mark/hobby/.gitignore | grep -E "^\.env$"
cat /home/mark/hobby/.env.example | grep OPENAI_API_KEY
ls /home/mark/hobby/templates /home/mark/hobby/agent /home/mark/hobby/api /home/mark/hobby/mcp /home/mark/hobby/tests
```
All five directories exist; .env appears as a standalone line in .gitignore; OPENAI_API_KEY appears in .env.example.
  </verify>
  <done>requirements.txt and requirements-dev.txt contain the four runtime and two dev packages respectively. .gitignore has a standalone `.env` line. .env.example has all four keys stubbed. All five directories exist.</done>
</task>

<task type="auto">
  <name>Task 2: Python source files — config.py, main.py, package stubs, HTML template</name>
  <files>
    config.py
    main.py
    templates/index.html
    agent/__init__.py
    api/__init__.py
    mcp/__init__.py
    tests/__init__.py
  </files>
  <action>
Create /home/mark/hobby/config.py with this exact content:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Stubbed for later phases — all optional in Phase 1
    openai_api_key: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
```

Create /home/mark/hobby/main.py with this exact content:
```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from config import settings  # noqa: F401 — ensures settings loaded and validated at startup

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2 will add MCP subprocess startup here
    yield
    # Phase 2 will add MCP subprocess shutdown here


app = FastAPI(
    title="Property Search Agent",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
```

CRITICAL — TemplateResponse signature: request is the FIRST argument, template name is second. The old style `TemplateResponse("index.html", {"request": request})` raises DeprecationWarning and will break. Use `templates.TemplateResponse(request, "index.html")` exactly as shown.

CRITICAL — Jinja2Templates path: uses `Path(__file__).parent / "templates"` (absolute path). This prevents TemplateNotFound errors when uvicorn is started from a directory other than the project root.

Create /home/mark/hobby/templates/index.html with this exact content:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Property Search</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto p-8">
        <h1 class="text-2xl font-bold">Property Search</h1>
        <p>Application loading...</p>
    </div>
</body>
</html>
```

Create /home/mark/hobby/agent/__init__.py with this exact content:
```python
"""Agent orchestration package. Implementation begins in Phase 3."""
```

Create /home/mark/hobby/api/__init__.py with this exact content:
```python
"""API route handlers. Implementation begins in Phase 4."""
```

Create /home/mark/hobby/mcp/__init__.py with this exact content:
```python
"""MCP subprocess management. Implementation begins in Phase 2."""
```

Create /home/mark/hobby/tests/__init__.py with this exact content:
```python
```
(empty file — makes tests/ a Python package so pytest can import from it)
  </action>
  <verify>
```bash
python3 -c "import ast; ast.parse(open('/home/mark/hobby/config.py').read()); print('config.py: valid syntax')"
python3 -c "import ast; ast.parse(open('/home/mark/hobby/main.py').read()); print('main.py: valid syntax')"
grep "TemplateResponse(request" /home/mark/hobby/main.py
grep "Path(__file__).parent" /home/mark/hobby/main.py
grep "cdn.tailwindcss.com" /home/mark/hobby/templates/index.html
grep "pydantic_settings" /home/mark/hobby/config.py
ls /home/mark/hobby/agent/__init__.py /home/mark/hobby/api/__init__.py /home/mark/hobby/mcp/__init__.py /home/mark/hobby/tests/__init__.py
```
All syntax checks pass; TemplateResponse uses request-first signature; templates path uses Path(__file__).parent; Tailwind CDN script tag present; pydantic_settings import (underscore, not hyphen) present; all four __init__.py files exist.
  </verify>
  <done>config.py defines Settings with four stubbed fields and a module-level singleton. main.py defines the FastAPI app with lifespan, /health, and / routes using the correct TemplateResponse(request, name) signature. templates/index.html is a valid HTML document with Tailwind CDN. All three package stubs and tests/__init__.py exist.</done>
</task>

<task type="auto">
  <name>Task 3: Tests, README, virtualenv install, and full verification</name>
  <files>
    tests/test_main.py
    README.md
  </files>
  <action>
Create /home/mark/hobby/tests/test_main.py with this exact content:
```python
from fastapi.testclient import TestClient

from main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_returns_html():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
```

CRITICAL — TestClient must be used as a context manager (`with TestClient(app) as client:`). Using it as a plain object (`client = TestClient(app)`) does not trigger lifespan startup/shutdown. Phase 2 will set state in lifespan; using the context manager now ensures tests remain correct after Phase 2.

No pytest-asyncio is needed. All test functions are plain `def`, not `async def`. TestClient is synchronous.

Create /home/mark/hobby/README.md with this exact content:
```markdown
# Property Search Agent

A LangGraph ReAct agent that accepts natural-language property search requests, navigates domain.com.au via a Playwright MCP subprocess, and streams results back through a FastAPI SSE API and single-page web UI.

## Requirements

- Python 3.12
- Node.js (required in Phase 2 for `@playwright/mcp`)

## Setup

```bash
# Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY (required in Phase 3+)
```

## Running

```bash
uvicorn main:app --reload
```

Server starts at http://localhost:8000

- `GET /` — HTML shell (property search UI)
- `GET /health` — health check: `{"status": "ok"}`

**Note:** When using `--reload`, uvicorn watches for file changes and restarts automatically. The MCP subprocess (added in Phase 2) does not restart automatically with uvicorn — restart the server manually after MCP configuration changes.

## Testing

```bash
pytest
```

## Project Structure

```
.
├── main.py              # FastAPI app, lifespan, routes
├── config.py            # Settings loaded from .env via pydantic-settings
├── requirements.txt     # Runtime dependencies
├── requirements-dev.txt # Dev dependencies (pytest, httpx)
├── .env.example         # Copy to .env and fill in values
├── templates/
│   └── index.html       # HTML shell (bare in Phase 1; full UI in Phase 5)
├── agent/               # LangGraph agent (Phase 3)
├── api/                 # SSE streaming routes (Phase 4)
├── mcp/                 # Playwright MCP subprocess lifecycle (Phase 2)
└── tests/
    └── test_main.py
```
```

Then run the following verification sequence. Execute each command and confirm it succeeds before continuing to the next:

**Step 1 — Create a fresh virtualenv and install dependencies:**
```bash
cd /home/mark/hobby
python3.12 -m venv .venv-verify
.venv-verify/bin/pip install -r requirements-dev.txt
```
Expected: pip installs fastapi, uvicorn, pydantic-settings, jinja2, pytest, httpx and their transitive dependencies with no errors.

**Step 2 — Run tests:**
```bash
cd /home/mark/hobby
.venv-verify/bin/pytest tests/ -v
```
Expected output:
```
tests/test_main.py::test_health PASSED
tests/test_main.py::test_index_returns_html PASSED
2 passed
```

**Step 3 — Start server and verify endpoints:**
```bash
cd /home/mark/hobby
.venv-verify/bin/uvicorn main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/health
curl -s -I http://localhost:8000/
kill %1
```
Expected: /health returns `{"status":"ok"}`, GET / returns HTTP 200 with content-type: text/html.

**Step 4 — Verify .env is gitignored:**
```bash
cd /home/mark/hobby
echo "TEST=1" > /home/mark/hobby/.env
git -C /home/mark/hobby check-ignore -v .env
rm /home/mark/hobby/.env
```
Expected: git outputs `.gitignore:XX:.env  .env` confirming .env is excluded.

**Step 5 — Clean up verification virtualenv:**
```bash
rm -rf /home/mark/hobby/.venv-verify
```

If step 1 fails: check that Python 3.12 is available as `python3.12`. If not available, use the system python3 and note it in the summary.
If step 2 fails: check for import errors — most likely cause is missing jinja2 (not in requirements.txt) or wrong pydantic import path in config.py.
If step 3 fails: check that uvicorn started (port conflict or import error at startup).
  </action>
  <verify>
All five steps above complete without errors. Specifically:
- `pytest` reports `2 passed`
- `curl http://localhost:8000/health` returns `{"status":"ok"}`
- `curl -I http://localhost:8000/` returns HTTP 200 with `content-type: text/html`
- `git check-ignore .env` confirms .env is excluded
  </verify>
  <done>tests/test_main.py has two passing tests. README.md documents setup, run, and test commands. pip install -r requirements.txt succeeds in a clean virtualenv. The server starts and serves both endpoints correctly. .env is confirmed gitignored.</done>
</task>

</tasks>

<verification>
After all tasks complete, the following must be true:

1. `uvicorn main:app` starts without errors — no ImportError, no AssertionError from Jinja2, no DeprecationWarning from TemplateResponse
2. `GET /health` returns `{"status": "ok"}` with HTTP 200
3. `GET /` returns HTTP 200 with Content-Type: text/html and a valid HTML document containing the Tailwind CDN script tag
4. `pytest tests/ -v` reports `2 passed, 0 failed`
5. `pip install -r requirements.txt` succeeds in a fresh Python 3.12 virtualenv (no missing packages, no version conflicts)
6. `git check-ignore .env` confirms .env is gitignored
7. .env.example is present and tracked by git (not gitignored)
8. config.py has no hardcoded secret values — all fields default to `""` or a safe public URL
9. All four directories (agent/, api/, mcp/, tests/) exist with __init__.py files
</verification>

<success_criteria>
- Server starts: `uvicorn main:app --reload` runs without errors and prints "Application startup complete"
- Health endpoint: `curl http://localhost:8000/health` returns `{"status":"ok"}`
- Index endpoint: `curl -I http://localhost:8000/` returns `HTTP/1.1 200 OK` with `content-type: text/html; charset=utf-8`
- Tests pass: `pytest tests/ -v` shows `2 passed`
- Clean install: `pip install -r requirements.txt` in a fresh virtualenv installs without errors
- Git hygiene: .env is gitignored, .env.example is tracked
- No hardcoded secrets: grep for "sk-" in config.py returns nothing
</success_criteria>

<output>
After completion, create `/home/mark/hobby/.planning/phases/01-foundation/01-foundation-01-SUMMARY.md` using the template at `.claude/get-shit-done/templates/summary.md`.

Key things to capture in the summary:
- Exact versions installed (capture from `pip freeze` output)
- Any deviations from the plan (e.g. if Python 3.12 was unavailable)
- The verified working state of the server
- Patterns established (TemplateResponse signature, TestClient context manager, pydantic_settings import path) — Phase 2 must follow these same patterns
</output>
