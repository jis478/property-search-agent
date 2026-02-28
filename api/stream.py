"""GET /stream/{run_id} — SSE generator with keep-alive and disconnect cleanup.

Consumes the asyncio.Queue populated by run_agent in api/search.py and yields
typed SSE events to the client. On disconnect (CancelledError from sse-starlette)
the finally block cancels the agent's asyncio task to stop browser activity.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.search import run_store

router = APIRouter()
logger = logging.getLogger(__name__)

# Keep-alive ping interval in seconds (send a comment line to prevent proxy timeouts)
_KEEPALIVE_SECONDS = 15


@router.get("/stream/{run_id}")
async def get_stream(run_id: str):
    """Stream SSE events for a search run.

    Yields typed events (thinking, tool_call, tool_result, complete, error) as
    they are placed on the run's queue by the background agent task.

    Sends a keep-alive ping every _KEEPALIVE_SECONDS to prevent proxy timeouts.

    On client disconnect: cancels the agent asyncio task and marks the run as
    cancelled. No resume capability — client must POST /search again to restart.
    """
    if run_id not in run_store:
        raise HTTPException(status_code=404, detail="run_id not found")

    async def sse_generator():
        run = run_store[run_id]
        queue: asyncio.Queue = run["queue"]
        try:
            while True:
                try:
                    # Use wait_for so we can send keep-alive pings and not block forever
                    item = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    # Send SSE comment (keep-alive ping — not a real event)
                    yield {"event": "ping", "data": ""}
                    continue
                if item is None:  # sentinel — agent finished
                    break
                yield {"event": item["type"], "data": json.dumps(item)}
        except asyncio.CancelledError:
            # sse-starlette cancels the task group on client disconnect
            # This propagates CancelledError to our await — we catch it here
            logger.info(f"Client disconnected from stream {run_id}")
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
