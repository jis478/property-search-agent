"""POST /search endpoint — run store, background agent task, SSE event translation.

Creates a new run_id UUID for each search request, starts the LangGraph agent
as an asyncio background task, and translates astream_events into typed SSE
event dicts stored on an asyncio.Queue for the /stream/{run_id} consumer.
"""
import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.exceptions import BotDetectedError, MCPError, StepLimitError

router = APIRouter()
logger = logging.getLogger(__name__)

# run_id -> {status, queue, task, query, _final_text}
# status values: "pending" | "running" | "complete" | "error" | "cancelled"
run_store: dict[str, dict[str, Any]] = {}

# Tracks the active run_id for 409 Conflict enforcement
_current_run_id: str | None = None

# ---------------------------------------------------------------------------
# Tool label map
# ---------------------------------------------------------------------------

TOOL_LABELS = {
    "browser_navigate": lambda args: f"Navigating to {args.get('url', '?')}",
    "browser_take_screenshot": lambda args: "Taking screenshot",
    "browser_wait_for": lambda args: "Waiting for page",
}

# ---------------------------------------------------------------------------
# Event translation helpers
# ---------------------------------------------------------------------------


def _condense_args(args: dict) -> dict:
    """Return a copy of args safe for json.dumps.

    - Drops internal LangGraph keys (e.g. 'runtime') that are not user-facing
    - Drops string values longer than 200 chars (base64 screenshots, etc.)
    - Converts any non-JSON-serializable value to its str() as a last resort
    """
    _INTERNAL_KEYS = {"runtime", "store", "config", "context"}
    result = {}
    for k, v in args.items():
        if k in _INTERNAL_KEYS:
            continue
        if isinstance(v, str) and len(v) > 200:
            continue
        try:
            json.dumps(v)
            result[k] = v
        except (TypeError, ValueError):
            result[k] = str(v)
    return result


def make_thinking(chunk_content: str) -> dict:
    """Produce a 'thinking' SSE event dict from a streaming LLM chunk."""
    return {"type": "thinking", "text": chunk_content}


def make_tool_call(name: str, args: dict) -> dict:
    """Produce a 'tool_call' SSE event dict."""
    label_fn = TOOL_LABELS.get(name, lambda a: name)
    return {
        "type": "tool_call",
        "tool": name,
        "label": label_fn(args),
        "args": _condense_args(args),
    }


def make_tool_result(name: str, output: Any, error: str | None) -> dict:
    """Produce a 'tool_result' SSE event dict."""
    return {
        "type": "tool_result",
        "tool": name,
        "success": error is None,
        "summary": str(output)[:200] if error is None else error,
    }


def make_complete(run_id: str, listings: list, partial: bool = False) -> dict:
    """Produce a 'complete' SSE event dict with extracted property listings."""
    return {
        "type": "complete",
        "run_id": run_id,
        "count": len(listings),
        "partial": partial,
        "listings": [l.model_dump() for l in listings],
    }


def make_error(exc: Exception) -> dict:
    """Produce an 'error' SSE event dict with a typed error_type field."""
    if isinstance(exc, BotDetectedError):
        error_type = "BotDetectedError"
    elif isinstance(exc, StepLimitError):
        error_type = "StepLimitError"
    elif isinstance(exc, MCPError):
        error_type = "MCPError"
    else:
        error_type = "UnknownError"
    return {
        "type": "error",
        "error_type": error_type,
        "message": str(exc),
    }


# ---------------------------------------------------------------------------
# Background agent coroutine
# ---------------------------------------------------------------------------


async def run_agent(run_id: str, agent, query: str) -> None:
    """Run the LangGraph agent in the background, pushing SSE events onto the queue.

    Translates astream_events v2 stream events into typed SSE dicts and places
    them on the run's asyncio.Queue for the SSE generator to consume.
    Sends a None sentinel when finished (normal or error) to signal end-of-stream.
    """
    global _current_run_id
    run = run_store[run_id]
    queue: asyncio.Queue = run["queue"]
    run["status"] = "running"
    try:
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": query}]},
            config={"recursion_limit": 15},
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    await queue.put(make_thinking(chunk.content))
                    # Accumulate full LLM text for post-loop listing extraction
                    run.setdefault("_final_text", "")
                    run["_final_text"] += chunk.content if isinstance(chunk.content, str) else ""
            elif kind == "on_tool_start":
                name = event["name"]
                args = event["data"].get("input", {}) or {}
                await queue.put(make_tool_call(name, args))
            elif kind == "on_tool_end":
                name = event["name"]
                output = event["data"].get("output")
                await queue.put(make_tool_result(name, output, None))

        # Parse listings from accumulated LLM text after astream_events exhaustion.
        # _final_text is populated during on_chat_model_stream handling above.
        from agent.url_builder import parse_listings_from_message

        import json as _json

        final_text = run.get("_final_text", "")
        # Detect partial results: check if the agent's JSON output had bot_detected=true.
        # parse_listings_from_message returns listings (not raises) when bot_detected=true
        # AND listings is non-empty — that is the partial-results contract from Phase 3.
        # parse_listings_from_message raises BotDetectedError only when bot_detected=true
        # AND listings is empty (full failure, no partial data).
        partial = False
        if final_text:
            try:
                _parsed = _json.loads(final_text)
                partial = bool(_parsed.get("bot_detected", False))
            except Exception:
                pass  # best-effort JSON check; partial stays False if parse fails
        listings = parse_listings_from_message(final_text) if final_text else []
        run["status"] = "complete"
        await queue.put(make_complete(run_id, listings, partial=partial))
    except asyncio.CancelledError:
        run["status"] = "cancelled"
        raise
    except Exception as exc:
        # BotDetectedError raised by parse_listings_from_message means bot was
        # detected AND zero listings were collected — this is a full failure.
        # All other exceptions (StepLimitError, MCPError, etc.) are also full failures.
        run["status"] = "error"
        await queue.put(make_error(exc))
    finally:
        await queue.put(None)  # sentinel — tells SSE generator to stop
        if _current_run_id == run_id:
            _current_run_id = None
        # TTL: remove run from store after 5 minutes
        asyncio.get_event_loop().call_later(300, lambda: run_store.pop(run_id, None))


# ---------------------------------------------------------------------------
# POST /search endpoint
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str


@router.post("/search", status_code=202)
async def post_search(body: SearchRequest, request: Request):
    """Accept a natural-language query, create a run, start the agent.

    Returns run_id immediately (HTTP 202 Accepted). The caller streams
    progress via GET /stream/{run_id}.

    Returns 409 Conflict if a search is already running (browser is busy).
    """
    global _current_run_id
    if _current_run_id is not None:
        raise HTTPException(status_code=409, detail="A search is already in progress")
    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    run_store[run_id] = {
        "status": "pending",
        "queue": queue,
        "task": None,
        "query": body.query,
        "_final_text": "",
    }
    agent = request.app.state.agent
    task = asyncio.create_task(run_agent(run_id, agent, body.query))
    run_store[run_id]["task"] = task
    _current_run_id = run_id
    return {"run_id": run_id}
