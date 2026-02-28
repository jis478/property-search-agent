# Phase 4: SSE Streaming API - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose the LangGraph agent as two FastAPI endpoints: `POST /search` (accepts natural-language query, returns `run_id`) and `GET /stream/{run_id}` (SSE stream with typed events). Phase 4 adds the streaming API layer only — no frontend, no new agent capabilities. The agent built in Phase 3 is the execution engine; this phase wires it to HTTP.

</domain>

<decisions>
## Implementation Decisions

### Event types and content
- Five typed events must be emitted: `thinking`, `tool_call`, `tool_result`, `complete`, `error`
- `thinking`: LLM reasoning text (the agent's narration as it decides what to do next)
- `tool_call`: Human-readable label + tool name + condensed args (e.g. "Navigating to https://domain.com.au/rent/richmond-vic/"). No raw base64 data.
- `tool_result`: Success/failure summary. No raw screenshot bytes in the stream.
- `complete`: Listings array + metadata — include `run_id`, `count`, `partial` flag (True when bot detected mid-run but listings were collected)
- `error`: Typed error — include `error_type` field (`BotDetectedError`, `StepLimitError`, `MCPError`) plus human-readable `message`
- Each SSE event uses `event:` field for the type and `data:` field as JSON

### Run storage and lifecycle
- In-memory dict keyed by `run_id` (UUID4) — no Redis or database needed for Phase 4
- Run state includes: status (`pending`, `running`, `complete`, `error`), queue of emitted events, asyncio task handle
- Completed runs persist for 5 minutes then are cleaned up (background task or TTL check on access)
- Each `POST /search` creates a new run regardless of duplicate queries

### Client disconnect behaviour
- When the SSE client disconnects, cancel the agent's asyncio task
- Use `asyncio.CancelledError` propagation — the agent task is cancelled, MCP calls in flight may complete but no further steps are taken
- On disconnect: mark run as `cancelled`, do not emit further events
- No "resume" capability — client must POST again to restart

### Concurrency model
- The Playwright MCP subprocess has a single browser instance — only one agent run can use the browser at a time
- Concurrent search requests are serialised: queue them or return 503 if a run is already active
- Simple approach: if a run is already `running`, return 409 Conflict with a message ("Browser is busy, try again shortly")
- No request queue for Phase 4 — caller retries on 409

### CORS
- CORS must permit `GET /stream/{run_id}` from any origin (browser EventSource on different port)
- Allow all origins for Phase 4 (tighten in production — deferred)
- Required headers: `Content-Type`, `Cache-Control`, `X-Accel-Buffering`

### Claude's Discretion
- SSE keep-alive ping interval
- Exact run_id format (UUID4 is fine)
- Background cleanup mechanism for expired runs
- Whether to use `asyncio.Queue` or `asyncio.Event` for event streaming internally
- How to hook into LangGraph execution to capture `thinking` and `tool_call` events (callback vs stream mode)

</decisions>

<specifics>
## Specific Ideas

- The `partial` flag on the `complete` event matters — Phase 5 frontend needs to signal "incomplete results" to the user when bot detection triggered mid-run (per Phase 3 partial-results contract)
- `error_type` in the `error` event matters — Phase 5 will show different UI messages for bot detection vs timeout vs MCP crash
- The 409 Conflict approach for busy browser keeps Phase 4 simple without a queue; Phase 5 UI can show "try again" messaging

</specifics>

<deferred>
## Deferred Ideas

- Request queue with position feedback — would require a Phase 4.1 insertion if needed
- Authentication / API keys on endpoints — out of scope for Phase 4
- Persisting run history to disk — separate concern
- Rate limiting — future phase or ops concern
- Tightening CORS to specific origins — production deployment concern

</deferred>

---

*Phase: 04-sse-streaming-api*
*Context gathered: 2026-02-28*
