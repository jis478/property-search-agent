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
