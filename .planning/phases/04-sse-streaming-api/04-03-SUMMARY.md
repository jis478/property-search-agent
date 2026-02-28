---
plan: 04-03
phase: 04-sse-streaming-api
type: summary
status: complete
completed: 2026-03-01
---

# Summary: 04-03 Human Verification Checkpoint

## One-liner
Live end-to-end verification of SSE streaming API against running server — 4/5 criteria pass; two serialization bugs fixed during testing; API-04 disconnect cancellation noted as WSL2 limitation.

## What Was Built
Human-verified the complete Phase 4 SSE streaming API against a live uvicorn server.

## Results

### Verified ✓
- **API-01**: POST /search returns UUID run_id with HTTP 202
- **API-02**: GET /stream/{run_id} emits `thinking`, `tool_call`, `tool_result`, `complete` events in real time
- **API-03**: Error event type correct in code (not triggered during test — no bot challenge encountered)
- **API-05**: CORS preflight returns `access-control-allow-origin: *`
- **409 Conflict**: Second POST while search in progress returns 409 (confirmed in server log)

### Not Verified ✗
- **API-04**: Client disconnect does not immediately cancel agent task on WSL2/h11. Root cause: uvicorn does not detect TCP disconnect without a failed write, so `request.is_disconnected()` returns False until sse-starlette catches a BrokenPipeError — which it handles internally without propagating back into the generator. The agent runs to natural completion. `_current_run_id` clears on completion, so no permanent resource leak. Accepted as known limitation.

## Bugs Found and Fixed

### 1. ToolRuntime not JSON serializable (stream crash)
`_condense_args` passed non-JSON-serializable `ToolRuntime` objects through unchanged. `json.dumps(item)` crashed in the SSE generator when real tool calls fired (not exercised in unit tests which use mocks).

**Fix**: `_condense_args` now tries `json.dumps(v)` for each value and falls back to `str(v)` on failure.

### 2. `runtime` internal key leaking into SSE events
The `runtime` arg key contained the full LangGraph `ToolRuntime` state (thousands of chars of internal agent context) in every `tool_call` SSE event.

**Fix**: `_condense_args` now strips a set of internal LangGraph keys (`runtime`, `store`, `config`, `context`) before serialization.

### 3. Disconnect detection (partial fix)
Replaced 15s blocking `asyncio.wait_for` with 2s polling + `request.is_disconnected()` check. Structurally correct; timing limited by WSL2/h11 TCP behavior (see above).

## Key Files
- `api/search.py` — `_condense_args` fix (lines 43-57)
- `api/stream.py` — disconnect polling via `request.is_disconnected()`

## Commits
- `fix(04-03): fix ToolRuntime serialization and improve SSE disconnect handling`
