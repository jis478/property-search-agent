# Property Search Agent

A LangGraph ReAct agent that accepts natural-language property search requests, navigates domain.com.au via a Playwright MCP subprocess, and streams results back through a FastAPI SSE API and single-page web UI.

## Requirements

- Python 3.12
- Node.js (required for `@playwright/mcp`)
- [Claude Code](https://claude.ai/code) (for dev skills and hooks)

## Setup

```bash
# Create and activate a conda environment (or venv)
conda create -n rental-search python=3.12
conda activate rental-search

# Install Python dependencies
pip install -r requirements-dev.txt

# Install Node dependencies (Playwright MCP)
npm install

# Configure environment
cp .env.example .env
# Edit .env and fill in:
#   OPENAI_API_KEY       — required (LangGraph agent)
#   GOOGLE_MAPS_API_KEY  — optional (school-distance filtering)
```

## Running

```bash
uvicorn main:app --reload
# or via skill:
/dev-server
```

Server starts at `http://localhost:8000`

| Endpoint | Description |
|---|---|
| `GET /` | Property search chat UI |
| `GET /health` | Health check |
| `GET /tools` | List registered MCP tools |
| `POST /search` | Start a search run, returns `run_id` |
| `GET /stream/{run_id}` | SSE stream of search progress and results |
| `POST /chat` | Conversational chat endpoint |

## Testing

```bash
pytest
# or via skill:
/lint
```

## Project Structure

```
.
├── main.py                  # FastAPI app, lifespan, routes
├── config.py                # Settings from .env via pydantic-settings
├── agent/
│   ├── __init__.py          # LangGraph ReAct property search agent
│   ├── chat_graph.py        # LangGraph chat workflow (async/sync tool routing)
│   ├── enrichment.py        # School-distance filtering via Google Maps API
│   ├── models.py            # PropertyListing Pydantic model
│   └── url_builder.py       # domain.com.au URL builder + listing parser
├── api/
│   ├── chat.py              # POST /chat endpoint
│   ├── search.py            # POST /search + SSE event translation
│   └── stream.py            # GET /stream/{run_id} SSE endpoint
├── mcp_subprocess/          # Playwright MCP subprocess lifecycle
├── templates/
│   └── index.html           # Single-page chat UI (noir concierge design)
├── tests/                   # pytest unit tests
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Dev dependencies
└── .env.example             # Environment variable reference
```

## Claude Code Skills

Project-scoped skills in `.claude/commands/` — available when working in this directory:

| Skill | Description |
|---|---|
| `/dev-server` | Start FastAPI with hot reload |
| `/run-search <query>` | Fire a search query and stream SSE results |
| `/check-agent` | Inspect MCP tools and agent health |
| `/test-enrichment [school]` | Smoke-test school-distance filtering |
| `/lint` | Run ruff + mypy across the codebase |
| `/preview` | Screenshot the UI with Playwright and review the design |

## Hooks

Configured in `.claude/settings.json`:

| Hook | Trigger | Action |
|---|---|---|
| `PostToolUse` | Edit or Write any `.py` file | Runs `ruff` linting automatically |

## Plugins

| Plugin | Source | Purpose |
|---|---|---|
| `frontend-design` | `claude-plugins-official` | Distinctive frontend UI generation |

## CI / GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | Push / PR to master | ruff lint + pytest |
| `claude.yml` | `@claude` mention in PR/issue | On-demand Claude response |
| `claude-code-review.yml` | PR opened / updated | Automatic Claude code review |
