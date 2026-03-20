# Phase 4: SSE Streaming API — Research

**Date:** 2026-03-01
**Status:** RESEARCH COMPLETE

---

## Key Question: How to capture LangGraph intermediate events?

**Answer: Use `agent.astream_events(input, config, version="v2")`**

LangGraph 1.0.10 exposes `astream_events` on compiled graphs (same interface as LangChain runnables). This yields typed event dicts with `event`, `name`, `data` fields. The relevant events:

| `event` value | When fired | Data |
|---|---|---|
| `on_chat_model_stream` | Each LLM output token | `{"chunk": AIMessageChunk(...)}` |
| `on_tool_start` | Before each tool call | `{"input": {"url": "...", ...}, "name": "browser_navigate"}` |
| `on_tool_end` | After each tool call | `{"output": ToolMessage(...)}` |
| `on_chain_end` (graph root) | Agent finishes | `{"output": {"messages": [...]}}` |

**Key finding:** `on_chat_model_stream` fires for every token. For `thinking` events we should buffer tokens and emit one `thinking` event per complete LLM reasoning step (when `on_chat_model_stream` stops), not per token — otherwise the SSE stream floods the client. A simpler approach: collect the full `AIMessage` content on `on_chain_end` of the `__main__` node and emit one `thinking` event per LLM turn.

**Filtering:** Use `include_names` or `include_tags` in `astream_events` to restrict to relevant nodes. Or filter by `event` type in the consumer loop.

**astream_events signature confirmed:**
```python
async for event in agent.astream_events(
    {"messages": [{"role": "user", "content": query}]},
    config={"recursion_limit": 15},
    version="v2",
):
    event_type = event["event"]
    event_name = event["name"]
    data = event["data"]
```

---

## Key Question: asyncio.Queue vs asyncio.Event for bridging?

**Answer: `asyncio.Queue` with `None` sentinel**

The architecture:
1. `POST /search` → creates `run_id`, creates `asyncio.Queue`, spawns background task via `asyncio.create_task`
2. Background task: calls `astream_events`, puts typed dicts into queue, puts `None` sentinel when done
3. `GET /stream/{run_id}` → SSE generator reads from queue, yields SSE events, exits on `None`

**Why Queue over Event:** Queue naturally buffers events between producer (background task) and consumer (SSE generator). Client may connect to `/stream` after the agent has already started — Queue ensures events aren't lost. `asyncio.Event` would lose events emitted before the consumer starts reading.

**Sentinel pattern confirmed:**
```python
# In background task (producer):
await queue.put({"type": "thinking", "text": "..."})
await queue.put(None)  # sentinel: stream done

# In SSE generator (consumer):
while True:
    item = await queue.get()
    if item is None:
        break
    yield ServerSentEvent(data=json.dumps(item), event=item["type"])
```

**`asyncio.create_task` vs `BackgroundTasks`:** Must use `asyncio.create_task` (not FastAPI `BackgroundTasks`). Reason: we need to store the `Task` object to call `.cancel()` on disconnect. `BackgroundTasks` runs after-response and doesn't expose the task handle.

---

## Key Question: Client disconnect detection and agent cancellation?

**How sse-starlette handles disconnects:**
- `EventSourceResponse` uses anyio task groups internally
- When client disconnects, `_listen_for_disconnect` fires and cancels the task group
- This propagates `CancelledError` into the async generator (`body_iterator`)
- sse-starlette calls `aclose()` on the generator if `send_timeout` fires

**Required pattern — SSE generator must use try/finally:**
```python
async def event_generator(run_id: str):
    run = run_store[run_id]
    try:
        while True:
            item = await run["queue"].get()
            if item is None:
                break
            yield {"event": item["type"], "data": json.dumps(item)}
    finally:
        # Client disconnected OR stream ended naturally
        task = run.get("task")
        if task and not task.done():
            task.cancel()
        run["status"] = "cancelled"
```

**Confirmed:** `CancelledError` propagates at the `await queue.get()` line when sse-starlette cancels the task group. The `finally` block fires regardless of whether the generator exits normally or via cancellation.

**Browser state after cancellation:** Safe. The `--isolated` flag on `@playwright/mcp` means no browser state persists between runs. `MCPManager.ready` stays `True` unless the MCP subprocess itself crashes. A new run after cancellation gets a clean browser context.

---

## Key Question: SSE wire format?

**`sse-starlette` confirmed installed** (version visible from test output). `EventSourceResponse` accepts an async generator yielding:
- `str` → wrapped in `data: {str}\n\n`
- `dict` → passed as `ServerSentEvent(**dict).encode()`
- `ServerSentEvent` object → `.encode()` called directly

**Wire format (confirmed from source inspection):**
```
id: 1\r\n
event: thinking\r\n
data: {"type": "thinking", "text": "..."}\r\n
\r\n
```

**Yield dict approach (cleanest):**
```python
yield {"event": "thinking", "data": json.dumps({"type": "thinking", "text": msg}), "id": str(counter)}
```

---

## Key Question: CORS for SSE?

**Add `CORSMiddleware` to FastAPI app:**
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**SSE-specific headers needed:**
- `Cache-Control: no-cache` — prevents buffering
- `X-Accel-Buffering: no` — disables nginx buffering (important for proxied deployments)
- `Content-Type: text/event-stream` — set by sse-starlette automatically

`EventSourceResponse` sets `Content-Type: text/event-stream` and `Cache-Control: no-cache` automatically. Add `X-Accel-Buffering: no` via `headers={"X-Accel-Buffering": "no"}` on the response.

---

## Key Question: Run storage structure?

**Confirmed in-memory dict pattern:**
```python
# In module scope (or app.state)
run_store: dict[str, dict] = {}

# Run record structure:
run_store[run_id] = {
    "status": "pending" | "running" | "complete" | "error" | "cancelled",
    "query": query,
    "queue": asyncio.Queue(),
    "task": None,           # asyncio.Task, set after create_task
    "created_at": time.monotonic(),
    "result": None,         # List[PropertyListing] on complete
    "error": None,          # error dict on error
}
```

**TTL cleanup:** Use `asyncio.get_running_loop().call_later(300, lambda: run_store.pop(run_id, None))` on run completion. This fires a sync callback after 300 seconds. Confirmed: `loop.call_later` exists on `asyncio.AbstractEventLoop`.

---

## Key Question: 409 Conflict for concurrent runs?

**Pattern:**
```python
# In POST /search handler:
active_runs = [r for r in run_store.values() if r["status"] == "running"]
if active_runs:
    raise HTTPException(status_code=409, detail="Browser is busy. Try again shortly.")
```

Track the currently running run_id separately (module-level `current_run_id: str | None = None`) for O(1) check instead of scanning.

---

## Key Question: How to translate LangGraph events to typed SSE events?

**Event mapping:**

| LangGraph event | SSE event type | Data to include |
|---|---|---|
| `on_chat_model_stream` (non-empty) | `thinking` | `{"text": chunk.content}` — only if content is str |
| `on_tool_start` | `tool_call` | `{"tool": name, "label": human_label, "args": condensed_args}` |
| `on_tool_end` | `tool_result` | `{"tool": name, "success": True/False, "summary": "..."}` |
| After `astream_events` exhausts | `complete` | `{"run_id": ..., "count": N, "partial": bool, "listings": [...]}` |
| Exception caught | `error` | `{"error_type": "BotDetectedError", "message": "..."}` |

**Human-readable tool labels:**
```python
TOOL_LABELS = {
    "browser_navigate": lambda args: f"Navigating to {args.get('url', '?')}",
    "browser_take_screenshot": lambda args: "Taking screenshot",
    "browser_wait_for": lambda args: f"Waiting for page",
}
```

**tool_result content:** Strip all image data. For `browser_take_screenshot`, the ToolMessage content includes image blocks (base64). Summary should just be `"Screenshot taken"`. For `browser_navigate`, check if ToolMessage text indicates success or error.

**complete event:** The `complete` event is emitted after `astream_events` exhausts. At that point, call `parse_listings_from_message(final_message.content)` to get `List[PropertyListing]`. Check if result is partial by catching `BotDetectedError` vs getting a list back (partial = True means BotDetectedError was raised internally but listings were collected — this is the Phase 3 partial-results contract).

---

## Installed packages confirmed

```
sse-starlette: installed (EventSourceResponse, ServerSentEvent available)
fastapi: installed with CORSMiddleware in fastapi.middleware.cors
pydantic v2: model_dump() returns JSON-serializable dicts
anyio: 4.12.1 (used internally by sse-starlette)
asyncio: stdlib, Queue.get() signature: (self) — wrap with asyncio.wait_for for timeout
uuid: stdlib, uuid4() produces 36-char strings like "9205bf46-6971-43fd-8bba-7021f2082f21"
```

---

## Existing codebase integration points

**`main.py`:** Has `app.state.mcp_tools` and `app.state.mcp_manager` set in lifespan. Phase 4 adds:
- Import `build_agent` from `agent` in lifespan, build agent on startup, store as `app.state.agent`
- Add `CORSMiddleware`
- Include new router (or add routes inline)

**`agent/__init__.py`:** Exports `build_agent`, `search_properties`, `PropertyListing`, `BotDetectedError`, `StepLimitError`, `MCPError`. Phase 4 uses `build_agent` and `BotDetectedError`/`StepLimitError`/`MCPError` for error translation.

**`agent/property_agent.py`:** `build_agent(mcp_tools)` returns compiled LangGraph graph. This graph supports `astream_events` because LangGraph compiled graphs inherit from LangChain's `Runnable`. Phase 4 uses `astream_events` directly on the agent graph, not `search_properties` (which uses `ainvoke`). The event mapping to SSE replaces the `search_properties` call.

**`agent/url_builder.py`:** `parse_listings_from_message(content)` still needed for the `complete` event — extract listings from the agent's final message.

---

## File structure for Phase 4

New files:
- `api/search.py` — POST /search endpoint + run store + agent background task
- `api/stream.py` — GET /stream/{run_id} SSE endpoint + event generator

Modified files:
- `main.py` — add CORSMiddleware, include API router, build agent in lifespan
- `tests/` — new test files for API endpoints

---

## RESEARCH COMPLETE
