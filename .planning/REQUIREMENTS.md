# Requirements: Domain Property Search Agent

**Defined:** 2026-02-19
**Core Value:** User types a natural-language property search request; the agent browses domain.com.au and returns structured listings with live streaming visibility into every step.

## v1 Requirements

### Agent Core

- [x] **AGNT-01**: Agent runs as a LangGraph ReAct graph using OpenAI GPT-4o as the LLM
- [x] **AGNT-02**: Agent extracts search parameters (suburb, price range, bedrooms, property type) from natural-language user input
- [x] **AGNT-03**: Agent constructs domain.com.au search URLs from extracted parameters (not form interaction)
- [x] **AGNT-04**: Agent enforces a recursion limit of 10 steps to prevent runaway LLM loops on tool failures or bot-blocked pages

### Scraping

- [x] **SCRP-01**: Playwright MCP server (`@playwright/mcp`) spawns as a subprocess at FastAPI startup and is cleanly shut down at FastAPI shutdown
- [x] **SCRP-02**: Agent navigates domain.com.au search results pages via Playwright MCP tools
- [x] **SCRP-03**: Agent extracts the following fields for each listing: address, price, bedrooms, bathrooms, property type, and listing URL
- [x] **SCRP-04**: Agent detects bot-challenged pages (Cloudflare/challenge title or minimal content) and handles gracefully rather than passing garbage to the LLM
- [x] **SCRP-05**: Agent aggregates results across up to 3 pages of search results (~75 listings maximum)

### API

- [ ] **API-01**: `POST /search` endpoint accepts a natural-language query, stores it, and returns a `run_id`
- [ ] **API-02**: `GET /stream/{run_id}` endpoint returns a Server-Sent Events stream for the agent run
- [ ] **API-03**: SSE stream emits typed events: `thinking` (LLM tokens), `tool_call` (tool invoked), `tool_result` (tool returned), `complete` (final listings), `error` (failure)
- [ ] **API-04**: SSE generator detects client disconnect and terminates the agent run to prevent resource leaks
- [ ] **API-05**: CORS is configured to allow browser `EventSource` connections

### Frontend

- [x] **FRNT-01**: Single HTML page is served by FastAPI (no Node.js/npm build step required)
- [ ] **FRNT-02**: User can type a natural-language property search query and submit it
- [ ] **FRNT-03**: Frontend displays an interpretation banner before searching (e.g. "Searching: 3 beds, Fitzroy VIC, $600k–$800k")
- [ ] **FRNT-04**: Frontend displays a live step log showing plain-English tool labels and the URL being navigated to, as the agent runs
- [ ] **FRNT-05**: Frontend renders property listing cards showing address, price, bedrooms, bathrooms, property type, and a clickable link to the domain.com.au listing
- [ ] **FRNT-06**: Frontend shows a friendly error state when the agent fails (bot detection, timeout, no results found)

## v2 Requirements

### Observability

- **OBS-01**: LangFuse `CallbackHandler` attached per request to trace LLM calls, tool invocations, latency, and token costs
- **OBS-02**: Each agent run is traceable in the LangFuse dashboard with `session_id` equal to `run_id`

### Enhanced Results

- **ENH-01**: Listing cards display a photo thumbnail (when extractable from search results page without additional requests)
- **ENH-02**: Result count displayed ("Found 47 listings across 2 pages")
- **ENH-03**: Land size extracted and shown on listing cards for house-type properties
- **ENH-04**: Copy results as JSON or markdown (single client-side button)

## Out of Scope

| Feature | Reason |
|---------|--------|
| User authentication / accounts | Zero value for single-user local dev tool |
| Map view | Requires geocoding + mapping library — distracts from core reliability |
| Saved searches / search history | Requires persistence layer — stateless design is correct for v1 |
| Price history / sold data | Requires separate API — not available on listing pages |
| Email / push alerts | Transforms scraper into monitoring service |
| Concurrent multi-suburb search | Race conditions with single browser context |
| Per-listing detail page scraping | 25x request multiplication, high bot-detection risk |
| Real-time auto-refresh | Continuous Playwright sessions trigger bot detection |
| Other property sites (realestate.com.au etc.) | domain.com.au only for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FRNT-01 | Phase 1 | Complete (2026-02-19) |
| SCRP-01 | Phase 2 | Complete |
| AGNT-01 | Phase 3 | Complete |
| AGNT-02 | Phase 3 | Complete |
| AGNT-03 | Phase 3 | Complete |
| AGNT-04 | Phase 3 | Complete |
| SCRP-02 | Phase 3 | Complete |
| SCRP-03 | Phase 3 | Complete |
| SCRP-04 | Phase 3 | Complete |
| SCRP-05 | Phase 3 | Complete |
| API-01 | Phase 4 | Pending |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 4 | Pending |
| FRNT-02 | Phase 5 | Pending |
| FRNT-03 | Phase 5 | Pending |
| FRNT-04 | Phase 5 | Pending |
| FRNT-05 | Phase 5 | Pending |
| FRNT-06 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after Phase 1 completion*
