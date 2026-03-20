# Property Search Agent — Claude Instructions

## Environment

- **Conda env**: `rental-search` (create with `conda create -n rental-search python=3.12`)
- Activate with `conda activate rental-search` before running anything
- **Python**: 3.12
- **Node.js**: required for `@playwright/mcp` (installed in `node_modules/`)

## Running the app

Start the server with the `/dev-server` skill or:
```
conda activate rental-search
uvicorn main:app --reload
```
Server runs at `http://localhost:8000`.

## Skills

| Skill | Purpose |
|---|---|
| `/dev-server` | Start FastAPI with hot reload |
| `/run-search` | Fire a test search query and pretty-print results |
| `/check-agent` | Inspect MCP tools, health, LangGraph graph |
| `/test-enrichment` | Smoke-test school-distance enrichment |
| `/lint` | Run ruff + mypy across the codebase |
| `/preview` | Screenshot app with Playwright and review UI design |

## Hooks

- **PostToolUse (Edit/Write)**: Automatically runs `ruff` on any edited `.py` file. Lint errors appear in the status line — fix them before moving on.

## Frontend

- Template: `templates/index.html` (single-page, Jinja2)
- Aesthetic: **Noir Concierge** — dark bg `#080808`, gold `#c9993a`, cream `#f0e6cc`
- Fonts: Cormorant Garamond (headings), JetBrains Mono (mono/code), DM Sans (body)
- No Tailwind — all custom CSS
- **Always run `/preview` after any change to `templates/index.html`**

## Code conventions

- Linting: `ruff` (configured in `pyproject.toml` or defaults)
- Type checking: `mypy`
- Tests: `pytest` (config in `pytest.ini`)
- All Python must pass `ruff check` before committing

## Architecture

- **FastAPI** (`main.py`) — serves UI and API endpoints
- **LangGraph ReAct agent** (`agent/`) — handles search reasoning
- **Playwright MCP subprocess** (`mcp_subprocess/`) — browser automation via `@playwright/mcp`
- **SSE streaming**: POST `/search` → returns `run_id` → GET `/stream/{run_id}` streams events
- **School-distance enrichment** (`agent/`) — uses Google Maps API (optional)

## Environment variables (`.env`)

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Yes | LangGraph agent |
| `GOOGLE_MAPS_API_KEY` | No | School-distance filtering |
