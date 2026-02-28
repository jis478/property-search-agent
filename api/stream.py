"""GET /stream/{run_id} — SSE generator with keep-alive and disconnect cleanup.

Consumes the asyncio.Queue populated by run_agent in api/search.py and yields
typed SSE events to the client. Disconnect is detected by polling
request.is_disconnected() on each queue-get timeout, which is more reliable
than waiting for CancelledError from sse-starlette.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from api.search import run_store

router = APIRouter()
logger = logging.getLogger(__name__)

# How often to poll for client disconnect (seconds). Also the keep-alive interval.
_POLL_SECONDS = 2


@router.get("/stream/{run_id}")
async def get_stream(run_id: str, request: Request):
    """Stream SSE events for a search run.

    Yields typed events (thinking, tool_call, tool_result, complete, error) as
    they are placed on the run's queue by the background agent task.

    Polls request.is_disconnected() every _POLL_SECONDS so disconnect is
    detected promptly and the agent task is cancelled to free the browser.
    """
    if run_id not in run_store:
        raise HTTPException(status_code=404, detail="run_id not found")

    async def sse_generator():
        run = run_store[run_id]
        queue: asyncio.Queue = run["queue"]
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_POLL_SECONDS)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        logger.info(f"Client disconnected from stream {run_id}")
                        break
                    # Still connected — send keep-alive ping
                    yield {"event": "ping", "data": ""}
                    continue
                if item is None:  # sentinel — agent finished
                    break
                yield {"event": item["type"], "data": json.dumps(item)}
        except asyncio.CancelledError:
            logger.info(f"Client disconnected (CancelledError) from stream {run_id}")
            raise
        finally:
            # On any exit (normal, disconnect, error): cancel the agent task
            task = run_store.get(run_id, {}).get("task")
            if task and not task.done():
                task.cancel()
                logger.info(f"Agent task cancelled for run {run_id}")
            current_status = run_store.get(run_id, {}).get("status")
            if current_status not in ("complete", "error"):
                if run_id in run_store:
                    run_store[run_id]["status"] = "cancelled"

    return EventSourceResponse(
        sse_generator(),
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
