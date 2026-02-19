# Phase 1: Foundation - Research

**Researched:** 2026-02-19
**Domain:** FastAPI project skeleton, pydantic-settings v2, Jinja2 templating
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**HTML Shell**
- Bare skeleton only — just `<html><head><body>` with a title; Phase 5 builds the real UI
- Tailwind CSS via CDN — no build step, loaded in `<head>` via CDN link
- Vanilla JS only — no frameworks; EventSource and DOM manipulation done directly
- Served via Jinja2 templates — `templates/index.html`, served with `TemplateResponse` (allows server-side value injection if needed later)

**Project Layout**
- Module-per-concern at root — `agent/`, `api/`, `mcp/` directories alongside `main.py` and `config.py`; no `src/` wrapper
- All planned dirs created now — `agent/`, `api/`, `mcp/` created as empty Python packages with `__init__.py` in Phase 1; stub modules added in later phases
- `.env.example` with all keys listed — developer copies to `.env` and fills in values (OpenAI, LangFuse keys stubbed even if deferred)
- Module-level Settings singleton — `settings = Settings()` in `config.py`, imported directly throughout the app

**Dev Workflow**
- Raw uvicorn command — documented in README: `uvicorn main:app --reload`
- `--reload` enabled by default — faster dev loop; note in README that MCP subprocess restart is manual
- Port 8000 — FastAPI default, documented in README
- `GET /health` endpoint — returns `{"status": "ok"}` — easy server-up verification

**Dependency Management**
- `requirements.txt` — simple, `pip install -r requirements.txt`; no pyproject.toml
- Compatible ranges — e.g. `fastapi>=0.115,<0.116`; allows patch updates, stays bounded
- Python 3.12 — target version, noted in README
- Separate `requirements-dev.txt` — pytest, httpx, and other dev-only packages separate from runtime deps

### Claude's Discretion
- Exact README structure and wording
- Whether to include a minimal FastAPI test in Phase 1 or defer testing to later phases
- `__init__.py` content for stub packages (empty or with a docstring)
- Jinja2 template engine vs StaticFiles mount (user chose templates/ location but implementation approach is open)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 1 establishes a runnable FastAPI application with environment-based config and a bare HTML page. The stack is small and well-understood: FastAPI (with Jinja2 for templating), pydantic-settings v2 (for config from `.env`), and uvicorn as the ASGI server. All Phase 1 dependencies have stable PyPI releases in early 2026 and the APIs researched here are current.

The original version range `fastapi>=0.115,<0.116` is valid but narrows to the 0.115.x patch series (latest: 0.115.14) while the ecosystem has moved to 0.128.x/0.129.x. A broader range like `>=0.115,<0.130` is more practical for fresh installs, but either works — the core APIs used here (lifespan, TemplateResponse, health endpoint) are stable across all versions from 0.115 onward. The recommendation is to widen to `>=0.115,<0.130` unless strict reproducibility across minor versions is required.

Two non-obvious facts verified by source inspection: (1) Jinja2 is NOT bundled with FastAPI — it must be listed explicitly in `requirements.txt`; (2) pydantic-settings v2 pulls in `python-dotenv` as a hard dependency, so dotenv loading works without explicitly adding python-dotenv to requirements.

**Primary recommendation:** Use `fastapi>=0.115,<0.130` to get the latest stable 0.128.x/0.129.x, list `jinja2>=3.1,<4` explicitly, and use the new `TemplateResponse(request, name)` signature throughout.

---

## Standard Stack

### Core (Phase 1 only)

| Library | Version Range | Actual Latest | Purpose | Why Standard |
|---------|--------------|--------------|---------|--------------|
| fastapi | `>=0.115,<0.130` | 0.129.0 | HTTP API framework + route definition | De facto Python async web standard |
| uvicorn[standard] | `>=0.30,<0.42` | 0.41.0 | ASGI server with websocket/http2 support | FastAPI's official recommended server |
| pydantic-settings | `>=2.5,<3` | 2.13.0 | Config from env vars / `.env` file | Official pydantic project, v2 API |
| jinja2 | `>=3.1,<4` | 3.1.6 | HTML template rendering | Required by starlette's Jinja2Templates |
| python-dotenv | pulled in by pydantic-settings | 1.2.1 | Parse `.env` files | Auto-installed as pydantic-settings hard dep — do NOT add separately |

**Key fact verified:** FastAPI does NOT bundle Jinja2. The starlette source asserts `"jinja2 must be installed to use Jinja2Templates"` and raises `AssertionError` at runtime if it is missing. List it explicitly.

**Key fact verified:** pydantic-settings DOES bundle python-dotenv as a hard dependency (`Requires-Dist: python-dotenv>=0.21.0`). Do not list python-dotenv separately — it will be present.

### Dev Dependencies

| Library | Version Range | Actual Latest | Purpose |
|---------|--------------|--------------|---------|
| pytest | `>=8.0,<10` | 9.0.2 | Test runner |
| httpx | `>=0.27,<0.29` | 0.28.1 | Required by starlette's TestClient |
| pytest-asyncio | NOT needed for Phase 1 | 1.3.0 | Only needed when tests use `async def` |

**pytest-asyncio note:** Phase 1 tests use `fastapi.testclient.TestClient` which is synchronous (inherits from `httpx.Client`). All Phase 1 test functions can be plain `def` functions. pytest-asyncio is not needed until async test functions are written (later phases).

**httpx note:** `TestClient` subclasses `httpx.Client` directly. httpx is a required test dependency, not optional.

### What to Explicitly Exclude from requirements.txt

- `python-dotenv` — pulled in by pydantic-settings automatically
- `python-multipart` — only needed for form/file uploads; Phase 1 has none
- `starlette` — installed as a FastAPI dependency automatically
- `pydantic` — installed as a FastAPI/pydantic-settings dependency automatically

### Installation

**requirements.txt:**
```
fastapi>=0.115,<0.130
uvicorn[standard]>=0.30,<0.42
pydantic-settings>=2.5,<3
jinja2>=3.1,<4
```

**requirements-dev.txt:**
```
-r requirements.txt
pytest>=8.0,<10
httpx>=0.27,<0.29
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# For development:
pip install -r requirements-dev.txt
```

---

## Architecture Patterns

### Recommended Project Structure

```
project-root/
├── main.py              # FastAPI app, lifespan, route registration
├── config.py            # Settings class + module-level singleton
├── requirements.txt
├── requirements-dev.txt
├── .env.example         # All keys stubbed (OPENAI, LANGFUSE, etc.)
├── .env                 # Gitignored — developer fills in
├── .gitignore
├── README.md
├── templates/
│   └── index.html       # Bare HTML shell served by GET /
├── agent/
│   └── __init__.py      # Empty package — stub for Phase 2+
├── api/
│   └── __init__.py      # Empty package — stub for Phase 3+
└── mcp/
    └── __init__.py      # Empty package — stub for Phase 2+
```

### Pattern 1: FastAPI Lifespan (asynccontextmanager)

The `@asynccontextmanager` lifespan pattern is the current standard. The old `@app.on_event("startup")` decorator is deprecated. Use lifespan from day one — Phase 2 (MCP subprocess) will add setup/teardown code here.

```python
# Source: FastAPI source inspection, FastAPI.__init__ signature (verified 0.128.5)
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup: add Phase 2+ initialization here ---
    yield
    # --- shutdown: add Phase 2+ cleanup here ---


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
```

**Extending for Phase 2:** The lifespan function receives `app: FastAPI`. To share state between lifespan and routes, assign to `app.state`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 2 will do: app.state.mcp_client = await create_mcp_client()
    yield
    # Phase 2 will do: await app.state.mcp_client.close()
```

### Pattern 2: pydantic-settings v2 Singleton

pydantic-settings v2 moved `BaseSettings` from `pydantic` to the separate `pydantic_settings` package. The import path changed in v2 — using the old path `from pydantic import BaseSettings` will fail with pydantic v2.

```python
# Source: pydantic_settings source, verified from /home/mark/miniconda3/lib/python3.13/site-packages/pydantic_settings/main.py
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",      # silently ignore keys in .env not defined here
    )

    # Phase 1: no required keys, but stub all future ones
    openai_api_key: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


# Module-level singleton — import this object, not the class
settings = Settings()
```

**Loading priority:** pydantic-settings loads from (highest to lowest priority): init kwargs → env vars → `.env` file → field defaults. An env var always wins over `.env` file.

**Usage elsewhere:**
```python
from config import settings

print(settings.openai_api_key)
```

### Pattern 3: Jinja2Templates Setup and TemplateResponse

```python
# Source: starlette/templating.py source inspection, verified TemplateResponse signature
# main.py
from fastapi.templating import Jinja2Templates

# Initialized at module level, not inside a function
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def index(request: Request):
    # New signature: request first, then template name
    # Old signature (TemplateResponse(name, {"request": request})) raises DeprecationWarning
    return templates.TemplateResponse(request, "index.html")
```

**CRITICAL — deprecated signature:** Many tutorials still show the old call style:
```python
# WRONG — raises DeprecationWarning in current starlette
return templates.TemplateResponse("index.html", {"request": request})
```

Use the new style always:
```python
# CORRECT — request is the first positional argument
return templates.TemplateResponse(request, "index.html")
# or with extra context:
return templates.TemplateResponse(request, "index.html", {"title": "My App"})
```

The `directory` path in `Jinja2Templates(directory="templates")` is relative to the process working directory (where uvicorn is launched). Always launch uvicorn from the project root.

### Pattern 4: Bare HTML Shell with Tailwind CDN

Tailwind CSS has two current versions as of February 2026:
- **v3.4.19** (v3-lts) — CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- **v4.2.0** (latest) — CDN via `@tailwindcss/browser` package on unpkg

Use Tailwind v3 CDN for Phase 1: simpler, widely documented, no config required. The `cdn.tailwindcss.com` script auto-detects classes and generates CSS at runtime.

```html
<!-- templates/index.html -->
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

Note: The Tailwind CDN play script is intended for development/prototyping. The CONTEXT.md decision ("Tailwind CSS via CDN — no build step") means this is the accepted approach for all phases.

### Pattern 5: Package Stubs

Empty packages should have a docstring `__init__.py`, not completely empty files. This makes the intent clear and prevents linter warnings about empty modules.

```python
# agent/__init__.py
"""Agent orchestration package. Stub for Phase 2."""

# api/__init__.py
"""API route handlers. Stub for Phase 3."""

# mcp/__init__.py
"""MCP subprocess management. Stub for Phase 2."""
```

### Anti-Patterns to Avoid

- **Old TemplateResponse signature:** `templates.TemplateResponse("index.html", {"request": request})` — raises `DeprecationWarning` in current starlette, will break in a future release. Use `templates.TemplateResponse(request, "index.html")`.
- **`from pydantic import BaseSettings`:** This was pydantic v1 only. In pydantic v2, `BaseSettings` was removed from the core package and lives in `pydantic_settings`. Will raise `ImportError`.
- **`@app.on_event("startup")`:** Deprecated. FastAPI will issue a deprecation warning. Use `@asynccontextmanager lifespan` instead.
- **Hardcoding API keys in `config.py` field defaults:** Use `""` as default and validate in a later phase. Never ship `openai_api_key: str = "sk-..."`.
- **`Jinja2Templates` inside route handlers:** Initialize once at module level, not inside each route call.
- **`pip install -r requirements.txt` without virtualenv:** The README must show virtualenv creation before the install command. Python 3.12 ships without pip in some OS-provided distributions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var loading | Custom `os.getenv()` chains with manual type casting | `pydantic_settings.BaseSettings` | Type validation, `.env` file support, nested models, priority ordering all built in |
| HTML template rendering | String concatenation or f-strings for HTML | `fastapi.templating.Jinja2Templates` | XSS escaping, inheritance, block inheritance for later phases |
| HTTP test client | Custom `requests` setup or raw socket tests | `fastapi.testclient.TestClient` | Handles ASGI lifecycle, triggers lifespan startup/shutdown in tests |
| App startup/shutdown | Module-level code that runs on import | `@asynccontextmanager lifespan` | Proper async lifecycle, access to `app.state`, Phase 2-ready |

**Key insight:** The FastAPI/starlette test ecosystem (`TestClient` backed by `httpx`) handles the full ASGI lifecycle including lifespan events. Never use raw `requests` for FastAPI testing.

---

## Common Pitfalls

### Pitfall 1: Jinja2 AssertionError at Startup

**What goes wrong:** `AssertionError: jinja2 must be installed to use Jinja2Templates` when the server starts, even though `from fastapi.templating import Jinja2Templates` succeeds.

**Why it happens:** `Jinja2Templates` is defined in starlette with a lazy import of jinja2. The class can be imported even when jinja2 is absent; the error fires at instantiation (`Jinja2Templates(directory=...)`).

**How to avoid:** List `jinja2>=3.1,<4` explicitly in `requirements.txt`. Do not assume it comes with FastAPI.

**Warning signs:** Server starts, import step succeeds, but instantiation at module level causes immediate crash on startup.

### Pitfall 2: Wrong pydantic-settings Import Path

**What goes wrong:** `ImportError: cannot import name 'BaseSettings' from 'pydantic'`

**Why it happens:** pydantic v2 removed `BaseSettings` from the core package. It now lives in the separate `pydantic_settings` package (underscore, not hyphen). Tutorials written for pydantic v1 show `from pydantic import BaseSettings`.

**How to avoid:** Always use `from pydantic_settings import BaseSettings, SettingsConfigDict`.

**Warning signs:** Works in an old virtualenv (pydantic v1), fails in a fresh Python 3.12 install.

### Pitfall 3: TemplateResponse Deprecation Warning

**What goes wrong:** `DeprecationWarning: The name is not the first parameter anymore.` in server logs, and the old style may stop working in a future starlette release.

**Why it happens:** Starlette changed the signature so `request` is the first positional argument. Most blog posts and StackOverflow answers still show the old style.

**How to avoid:** Always use `templates.TemplateResponse(request, "index.html")`. The request object is always the first argument.

**Warning signs:** Working code that produces deprecation warnings — silent now, breaking later.

### Pitfall 4: TestClient Not Triggering Lifespan

**What goes wrong:** Tests pass but lifespan startup code never runs; state set in lifespan is `None` in routes during tests.

**Why it happens:** `TestClient(app)` as a plain object does not run lifespan. It must be used as a context manager: `with TestClient(app) as client:`.

**How to avoid:**
```python
# CORRECT: lifespan runs
with TestClient(app) as client:
    response = client.get("/health")

# WRONG: lifespan does NOT run
client = TestClient(app)
response = client.get("/health")
```

**Warning signs:** Tests pass but any route that relies on `app.state` set in lifespan throws `AttributeError`.

### Pitfall 5: templates/ directory relative path

**What goes wrong:** `jinja2.exceptions.TemplateNotFound: index.html` when uvicorn is started from a directory other than the project root.

**Why it happens:** `Jinja2Templates(directory="templates")` resolves relative to the current working directory (cwd), not relative to `main.py`.

**How to avoid:** Either always run `uvicorn main:app` from project root, OR use an absolute path:
```python
from pathlib import Path
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
```

The absolute-path approach is more robust. Recommended for production but the relative path is acceptable if documented.

**Warning signs:** Works in IDE terminal, fails when launched as a system service.

### Pitfall 6: `.env` file not loaded in tests

**What goes wrong:** Settings fields that are required (no default) raise `ValidationError` during tests because `.env` is not present or is not in the test working directory.

**Why it happens:** pydantic-settings looks for `.env` relative to the process cwd. pytest may run from a different directory.

**How to avoid for Phase 1:** Give all Settings fields default values (use `""` for string keys). For later phases when keys are truly required, use `pytest`'s `tmp_path` fixture or `monkeypatch.setenv()`.

**Warning signs:** Tests fail only in CI, pass locally; CI runs pytest from a different directory.

---

## Code Examples

Verified patterns from source inspection and runtime testing:

### Complete main.py

```python
# Source: verified against FastAPI 0.128.5, starlette 0.52.1
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from config import settings  # noqa: F401 — ensure settings loaded on startup

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

### Complete config.py

```python
# Source: pydantic_settings source verified, pattern tested with pydantic-settings 2.12.0
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

### Complete .env.example

```bash
# Copy to .env and fill in your values
# Required for Phase 3+ (agent):
OPENAI_API_KEY=sk-...

# Required for Phase 4+ (observability, optional):
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Standard .gitignore (Python project)

```gitignore
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

# Environment / secrets
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

### Minimal Phase 1 test (tests/test_main.py)

```python
# Source: starlette TestClient verified in source inspection
import pytest
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

Note: No `pytest-asyncio` needed. All tests use synchronous `TestClient`.

---

## State of the Art (Early 2026)

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `from pydantic import BaseSettings` | `from pydantic_settings import BaseSettings` | pydantic v2 (2023) | Hard import error with pydantic v2 |
| `@app.on_event("startup")` | `@asynccontextmanager lifespan` | FastAPI 0.93+ (2023) | DeprecationWarning; lifespan won't run in future |
| `TemplateResponse("name", {"request": r})` | `TemplateResponse(request, "name")` | starlette 0.37 (2023) | DeprecationWarning; will break eventually |
| `fastapi>=0.115,<0.116` (original) | `fastapi>=0.115,<0.130` (recommended) | N/A | 0.115.14 is installable but 0.128.x/0.129.x are current |
| Tailwind v3 `cdn.tailwindcss.com` | Same (v3-lts still at 3.4.19) | v4 released Jan 2025 | v3 CDN still works; v4 requires `@tailwindcss/browser` |

**Deprecated/outdated (do not use):**
- `@app.on_event`: Works but deprecated since FastAPI 0.93
- `BaseSettings` from `pydantic` core: Removed in pydantic v2; pydantic v1 is EOL
- `python-dotenv` explicit install: pydantic-settings installs it automatically
- `pytest-asyncio` for sync TestClient tests: Unnecessary overhead for Phase 1

---

## Version Pinning Recommendation

The original decision used `fastapi>=0.115,<0.116` as an example of "compatible ranges." The actual recommendation for 2026:

| Package | Original Decision | Recommended | Rationale |
|---------|-----------------|-------------|-----------|
| fastapi | `>=0.115,<0.116` | `>=0.115,<0.130` | Installs 0.129.0 (current). All APIs used here stable across the range. 0.115.x installs 0.115.14 which is valid but 14 minor versions old. |
| uvicorn[standard] | `>=0.30,<0.32` | `>=0.30,<0.42` | Latest is 0.41.0, wide range is safe for a server with stable API |
| pydantic-settings | unspecified | `>=2.5,<3` | Latest is 2.13.0; 2.x series is stable |
| jinja2 | unspecified | `>=3.1,<4` | Latest is 3.1.6; 3.x series is stable |

If strict reproducibility is required (reproducing exact versions), use `pip freeze > requirements.lock` separately rather than tightening the ranges in `requirements.txt`.

---

## Open Questions

1. **Tailwind v3 vs v4 CDN**
   - What we know: Tailwind v3 CDN (`cdn.tailwindcss.com`) still works. v4 CDN requires `@tailwindcss/browser` via unpkg. v3-lts is 3.4.19, v4 latest is 4.2.0.
   - What's unclear: Whether the Phase 5 UI work expects v4 features or if v3 is sufficient.
   - Recommendation: Use v3 CDN for Phase 1 (locked decision is "Tailwind via CDN, no build step"). Phase 5 can upgrade if needed — just change the `<script>` tag.

2. **pytest-asyncio in requirements-dev.txt**
   - What we know: Phase 1 has no async test functions; `TestClient` is synchronous.
   - What's unclear: Whether the planner wants to pre-install pytest-asyncio for later phases now.
   - Recommendation: Omit from Phase 1 `requirements-dev.txt`. Add it in Phase 2 or 3 when async tests are first written.

3. **uvicorn `--reload` with MCP subprocesses (Phase 2 concern)**
   - What we know: The CONTEXT.md notes "MCP subprocess restart is manual" with `--reload`.
   - What's unclear: Whether uvicorn watch patterns (`--reload-include`) need configuring.
   - Recommendation: Out of scope for Phase 1. Flag in README as noted in CONTEXT.md.

---

## Sources

### Primary (HIGH confidence)
- FastAPI 0.128.5 source (`/home/mark/miniconda3/envs/rental-search/lib/python3.11/site-packages/fastapi/`) — lifespan signature, Jinja2Templates, TemplateResponse
- starlette 0.52.1 source (`starlette/templating.py`, `starlette/testclient.py`) — TemplateResponse signature, TestClient inheritance from httpx.Client
- pydantic_settings 2.12.0 source (`/home/mark/miniconda3/lib/python3.13/site-packages/pydantic_settings/`) — BaseSettings, SettingsConfigDict, DotEnvSettingsSource
- pydantic-settings 2.13.0 dist-info METADATA — `Requires-Dist: python-dotenv>=0.21.0` (confirmed hard dependency)
- PyPI `pip index versions` output — all version ranges verified live against PyPI on 2026-02-19

### Secondary (MEDIUM confidence)
- npm registry (`npm show tailwindcss dist-tags`) — confirmed v3-lts=3.4.19, latest=4.2.0 (verified live)
- Python runtime tests — `TestClient` with lifespan verified working against FastAPI 0.128.5

### Tertiary (LOW confidence)
- Starlette 0.37 TemplateResponse signature change date — from code comments in starlette/templating.py, not from a changelog entry

---

## Metadata

**Confidence breakdown:**
- Standard stack versions: HIGH — verified live from PyPI on 2026-02-19
- FastAPI/Jinja2 integration pattern: HIGH — verified from installed source code
- pydantic-settings v2 pattern: HIGH — verified from pydantic_settings package source
- TemplateResponse signature: HIGH — verified from starlette source
- lifespan pattern: HIGH — verified by running test in Python 3.11 against FastAPI 0.128.5
- Tailwind CDN version: HIGH — verified via npm registry live
- pytest-asyncio recommendation: HIGH — verified by inspecting TestClient class hierarchy

**Research date:** 2026-02-19
**Valid until:** 2026-08-19 (6 months; these are stable APIs with slow churn)
