# Roadmap: Domain Property Search Agent

## Overview

Build a LangGraph ReAct agent that accepts natural-language property search requests, uses a Playwright MCP subprocess to navigate domain.com.au, and streams results back to the user via a FastAPI SSE API and a single-page web UI. The build order follows strict dependencies: foundation first, then MCP subprocess lifecycle (the highest-risk infrastructure piece), then agent correctness without streaming, then streaming API, then the frontend that depends on a stable API contract.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - FastAPI project skeleton, config management, and static file serving
- [ ] **Phase 2: MCP Integration** - Playwright MCP subprocess spawns at startup and exposes browser tools
- [ ] **Phase 3: LangGraph Agent** - Agent browses domain.com.au and returns structured listings (no streaming)
- [ ] **Phase 4: SSE Streaming API** - Streaming endpoints expose agent events to callers
- [ ] **Phase 5: Frontend** - Single-page UI connects to SSE stream and renders listing cards end-to-end

## Phase Details

### Phase 1: Foundation
**Goal**: A running FastAPI server with config management, git hygiene, and the HTML shell served — the safe base from which all other phases build
**Depends on**: Nothing (first phase)
**Requirements**: FRNT-01
**Success Criteria** (what must be TRUE):
  1. `uvicorn main:app` starts without errors and responds to `GET /` with the HTML page
  2. API keys and secrets are loaded from environment variables via pydantic-settings, never hardcoded
  3. `.gitignore` excludes `.env`, `__pycache__`, and virtualenv directories
  4. The project installs cleanly from `requirements.txt` in a fresh virtualenv
**Plans**: 1 plan

Plans:
- [x] 01-foundation-01-PLAN.md — FastAPI skeleton: dependencies, config, HTML shell, package stubs, tests, git hygiene

### Phase 2: MCP Integration
**Goal**: The Playwright MCP subprocess starts when FastAPI starts, registers browser automation tools that the agent can call, and shuts down cleanly without leaving zombie Chromium processes
**Depends on**: Phase 1
**Requirements**: SCRP-01
**Success Criteria** (what must be TRUE):
  1. FastAPI startup launches the `@playwright/mcp` Node.js subprocess and connects via stdio
  2. Available MCP tools (navigate, screenshot, click, etc.) are enumerable from a test endpoint or startup log
  3. FastAPI shutdown terminates the MCP subprocess and all Chromium child processes cleanly
  4. Restarting the server multiple times does not accumulate zombie processes
**Plans**: 2 plans

Plans:
- [ ] 02-mcp-integration-01-PLAN.md — MCPManager class, FastAPI lifespan wiring, /health and /tools endpoints
- [ ] 02-mcp-integration-02-PLAN.md — Test suite: mock fixture for MCPManager, updated /health tests, new unit tests

### Phase 3: LangGraph Agent
**Goal**: The agent accepts a natural-language property query, extracts parameters, constructs domain.com.au search URLs, navigates up to 3 pages, and returns structured listings — verified correct before any streaming is added
**Depends on**: Phase 2
**Requirements**: AGNT-01, AGNT-02, AGNT-03, AGNT-04, SCRP-02, SCRP-03, SCRP-04, SCRP-05
**Success Criteria** (what must be TRUE):
  1. A test script calling the agent with a plain-English query returns a list of listing dicts with address, price, bedrooms, bathrooms, property type, and listing URL
  2. The agent constructs a domain.com.au search URL directly from extracted parameters — it never interacts with the search form
  3. When domain.com.au returns a bot-challenge page, the agent returns a clear error rather than garbled listing data
  4. The agent stops after at most 10 LangGraph steps and raises a recoverable error instead of looping indefinitely
  5. Results span up to 3 pages of search results (approximately 75 listings) when available
**Plans**: TBD

### Phase 4: SSE Streaming API
**Goal**: Two FastAPI endpoints expose the running agent as a Server-Sent Events stream, with all typed event categories emitted, client disconnect handled, and CORS configured for browser use
**Depends on**: Phase 3
**Requirements**: API-01, API-02, API-03, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. `POST /search` accepts a natural-language query and returns a JSON body containing a `run_id`
  2. `GET /stream/{run_id}` returns a valid SSE stream that emits `thinking`, `tool_call`, `tool_result`, `complete`, and `error` typed events
  3. Closing the browser tab (or `curl --max-time`) stops the agent run — no resource leak from abandoned streams
  4. An `EventSource` connection from a browser on a different port succeeds (CORS does not block it)
**Plans**: TBD

### Phase 5: Frontend
**Goal**: The single-page UI is fully wired to the SSE API — a user types a query, watches live agent steps appear, and sees structured listing cards on completion
**Depends on**: Phase 4
**Requirements**: FRNT-02, FRNT-03, FRNT-04, FRNT-05, FRNT-06
**Success Criteria** (what must be TRUE):
  1. User types a natural-language query in the text field and submits it — the page shows an interpretation banner (e.g. "Searching: 3 beds, Fitzroy VIC, $600k–$800k") before any results appear
  2. While the agent runs, a live step log updates in real time showing plain-English tool labels and the URL being navigated
  3. When the agent completes, property listing cards appear showing address, price, bedrooms, bathrooms, property type, and a clickable link to the domain.com.au listing page
  4. When the agent fails (bot detection, timeout, or zero results), the page displays a friendly human-readable error message instead of a blank state or raw JSON
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/1 | Complete | 2026-02-19 |
| 2. MCP Integration | 0/2 | Not started | - |
| 3. LangGraph Agent | 0/TBD | Not started | - |
| 4. SSE Streaming API | 0/TBD | Not started | - |
| 5. Frontend | 0/TBD | Not started | - |
