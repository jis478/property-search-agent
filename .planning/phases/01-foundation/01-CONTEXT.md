# Phase 1: Foundation - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

FastAPI project skeleton that serves a bare-bones HTML shell, loads all config from environment variables via pydantic-settings, and establishes git hygiene (.gitignore, .env.example). This phase delivers a running server with a /health endpoint and GET / returning index.html — nothing more. MCP integration, agent logic, and full UI wiring are separate phases.

</domain>

<decisions>
## Implementation Decisions

### HTML Shell
- **Bare skeleton only** — just `<html><head><body>` with a title; Phase 5 builds the real UI
- **Tailwind CSS via CDN** — no build step, loaded in `<head>` via CDN link
- **Vanilla JS only** — no frameworks; EventSource and DOM manipulation done directly
- **Served via Jinja2 templates** — `templates/index.html`, served with `TemplateResponse` (allows server-side value injection if needed later)

### Project Layout
- **Module-per-concern at root** — `agent/`, `api/`, `mcp/` directories alongside `main.py` and `config.py`; no `src/` wrapper
- **All planned dirs created now** — `agent/`, `api/`, `mcp/` created as empty Python packages with `__init__.py` in Phase 1; stub modules added in later phases
- **`.env.example` with all keys listed** — developer copies to `.env` and fills in values (OpenAI, LangFuse keys stubbed even if deferred)
- **Module-level Settings singleton** — `settings = Settings()` in `config.py`, imported directly throughout the app

### Dev Workflow
- **Raw uvicorn command** — documented in README: `uvicorn main:app --reload`
- **`--reload` enabled by default** — faster dev loop; note in README that MCP subprocess restart is manual
- **Port 8000** — FastAPI default, documented in README
- **`GET /health` endpoint** — returns `{"status": "ok"}` — easy server-up verification

### Dependency Management
- **`requirements.txt`** — simple, `pip install -r requirements.txt`; no pyproject.toml
- **Compatible ranges** — e.g. `fastapi>=0.115,<0.116`; allows patch updates, stays bounded
- **Python 3.12** — target version, noted in README
- **Separate `requirements-dev.txt`** — pytest, httpx, and other dev-only packages separate from runtime deps

### Claude's Discretion
- Exact README structure and wording
- Whether to include a minimal FastAPI test in Phase 1 or defer testing to later phases
- `__init__.py` content for stub packages (empty or with a docstring)
- Jinja2 template engine vs StaticFiles mount (user chose templates/ location but implementation approach is open)

</decisions>

<specifics>
## Specific Ideas

- README should show the uvicorn command explicitly — developer should be able to get running from README alone
- `.env.example` should stub ALL keys that will eventually be needed (OPENAI_API_KEY, LANGFUSE_* even if deferred) so the developer sets them up once

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-19*
