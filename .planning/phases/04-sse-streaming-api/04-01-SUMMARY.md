---
phase: 04-sse-streaming-api
plan: "01"
subsystem: api
tags: [fastapi, sse, asyncio, langgraph, sse-starlette, streaming]

# Dependency graph
requires:
  - phase: 03-langgraph-agent
    provides: build_agent, astream_events v2, BotDetectedError/StepLimitError/MCPError exceptions, parse_listings_from_message, PropertyListing model
provides:
  - POST /search FastAPI router with run_store and background agent task
  - GET /stream/{run_id} FastAPI router with SSE generator and disconnect cleanup
  - Five typed SSE event dicts: thinking, tool_call, tool_result, complete, error
  - asyncio.Queue-based event pipeline from agent to SSE consumer
affects:
  - 04-02-PLAN (main.py integration — mounts these routers)
  - 04-03-PLAN (end-to-end SSE tests)
  - 05-frontend (consumes /search and /stream/{run_id} endpoints)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "astream_events v2 translation: on_chat_model_stream->thinking, on_tool_start->tool_call, on_tool_end->tool_result"
    - "asyncio.Queue as in-process event bus between background task and SSE generator"
    - "asyncio.create_task for non-blocking agent execution returning immediately with run_id"
    - "asyncio.wait_for with timeout for SSE keep-alive ping injection"
    - "_final_text accumulation pattern: concatenate on_chat_model_stream chunks, parse after loop exhaustion"
    - "None sentinel on asyncio.Queue signals end-of-stream"
    - "task.cancel() in finally block ensures browser cleanup on client disconnect"

key-files:
  created:
    - api/search.py
    - api/stream.py
  modified: []

key-decisions:
  - "run_store is a module-level dict (not class) — api/stream.py imports it by reference so both modules share the same dict instance"
  - "_final_text accumulated from on_chat_model_stream chunks post-loop — astream_events does not provide a final-message event, so text must be collected incrementally"
  - "partial flag derived from bot_detected JSON field before calling parse_listings_from_message — avoids re-parsing JSON twice"
  - "_condense_args drops str values >200 chars — prevents base64 screenshot data leaking into tool_call SSE events"
  - "asyncio.wait_for(timeout=15) for keep-alive — prevents queue.get() blocking indefinitely and allows ping injection without a separate task"
  - "409 Conflict on concurrent /search — simple stateless check via _current_run_id module-level var; no queue needed for Phase 4"

patterns-established:
  - "SSE event format: {event: item['type'], data: json.dumps(item)} — type field doubles as SSE event name and payload discriminator"
  - "Disconnect cleanup: finally block in sse_generator cancels agent task regardless of exit reason"
  - "Status lifecycle: pending -> running -> complete|error|cancelled"

requirements-completed: [API-01, API-02, API-03, API-04]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 4 Plan 01: SSE Streaming API Route Modules Summary

**FastAPI POST /search and GET /stream/{run_id} SSE endpoints using asyncio.Queue pipeline from LangGraph astream_events v2 to typed client events**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T20:35:49Z
- **Completed:** 2026-02-28T20:37:43Z
- **Tasks:** 2 completed
- **Files modified:** 2 created

## Accomplishments

- `api/search.py` implements POST /search with run_store dict, asyncio.Queue pipeline, and background run_agent coroutine that drives agent.astream_events v2 and translates all five event types
- `api/stream.py` implements GET /stream/{run_id} with EventSourceResponse, 15-second keep-alive pings, and finally-block task cancellation on client disconnect
- All five SSE event types implemented: thinking (LLM reasoning text), tool_call (condensed args + human label), tool_result (success/failure summary), complete (listings + partial flag), error (typed error_type)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create api/search.py** - `4764578` (feat)
2. **Task 2: Create api/stream.py** - `56370a9` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `api/search.py` — POST /search endpoint, run_store dict, run_agent coroutine, make_thinking/make_tool_call/make_tool_result/make_complete/make_error helpers, _condense_args, TOOL_LABELS
- `api/stream.py` — GET /stream/{run_id} SSE generator with asyncio.wait_for keep-alive, CancelledError handling, and finally-block agent task cancellation

## Decisions Made

- `run_store` is imported by reference in `api/stream.py` from `api.search` — both modules share the same dict instance without needing a shared state layer
- `_final_text` accumulation during `on_chat_model_stream` is the only reliable way to get the agent's final JSON output from astream_events (there is no "on_agent_finish" event in LangGraph v2 astream_events)
- `partial` flag check uses a best-effort JSON parse of `_final_text` before calling `parse_listings_from_message` — if JSON parsing fails, `partial` stays False and full parsing proceeds normally
- `_condense_args` drops string values over 200 chars to prevent base64 screenshot data appearing in `tool_call` events

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both routers are ready for inclusion in `main.py` via Plan 02
- `api/__init__.py` may need updating to expose the routers (Plan 02 handles this)
- CORS middleware needed in main.py — not added here per plan instructions

---
*Phase: 04-sse-streaming-api*
*Completed: 2026-02-28*
