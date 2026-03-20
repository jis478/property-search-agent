"""POST /chat — conversational endpoint backed by a LangGraph workflow.

The chat graph decides whether the user needs a property search (async tool)
or can be answered directly. When a search is requested the endpoint starts
a background agent task and returns a ``run_id`` so the frontend can subscribe
to ``/stream/{run_id}`` for real-time progress — exactly the same SSE infra
used by ``/search``.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Request
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage as LCToolMessage,
)
from pydantic import BaseModel

from agent.chat_graph import ASYNC_TOOLS, CHAT_SYSTEM_PROMPT
from api.search import run_agent, run_store

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ToolCallInfo(BaseModel):
    id: str
    name: str
    args: Dict[str, Any]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: Optional[List[ToolCallInfo]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    run_id: Optional[str] = None
    tool_call: Optional[ToolCallInfo] = None


# ---------------------------------------------------------------------------
# Message conversion
# ---------------------------------------------------------------------------


def _to_langchain_messages(msgs: List[ChatMessage]) -> list:
    """Convert frontend chat messages to LangChain message objects."""
    result = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]
    for m in msgs:
        if m.role == "user":
            result.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            if m.tool_calls:
                result.append(
                    AIMessage(
                        content=m.content,
                        tool_calls=[
                            {
                                "id": tc.id,
                                "name": tc.name,
                                "args": tc.args,
                                "type": "tool_call",
                            }
                            for tc in m.tool_calls
                        ],
                    )
                )
            else:
                result.append(AIMessage(content=m.content))
        elif m.role == "tool" and m.tool_call_id:
            result.append(
                LCToolMessage(content=m.content, tool_call_id=m.tool_call_id)
            )
    return result


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Conversational chat with LangGraph tool-calling workflow.

    Returns immediately. If the LLM decides to search properties, the
    response includes a ``run_id`` + ``tool_call`` so the frontend can
    subscribe to SSE and later record the tool result in its history.
    """
    import api.search as search_mod

    chat_graph = request.app.state.chat_graph
    lc_messages = _to_langchain_messages(body.messages)

    result = await chat_graph.ainvoke({"messages": lc_messages})

    last_msg = result["messages"][-1]

    # -- Async tool requested (search_properties) ---------------------------
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        for tc in last_msg.tool_calls:
            if tc["name"] in ASYNC_TOOLS:
                if search_mod._current_run_id is not None:
                    return ChatResponse(
                        reply=(last_msg.content or "")
                        + "\n\nA search is already running. Please wait for it to finish.",
                    )

                query = tc["args"].get("query", "")
                school = tc["args"].get("school") or None
                max_dist = tc["args"].get("max_distance_meters")
                logger.info(
                    "search_properties tool_call: query=%r school=%r max_distance_meters=%s",
                    query, school, max_dist,
                )
                if max_dist is not None:
                    try:
                        max_dist = int(max_dist)
                    except (TypeError, ValueError):
                        max_dist = None
                run_id = str(uuid.uuid4())
                queue: asyncio.Queue = asyncio.Queue()
                run_store[run_id] = {
                    "status": "pending",
                    "queue": queue,
                    "task": None,
                    "query": query,
                    "_final_text": "",
                    "school_address": school,
                    "max_distance_meters": max_dist,
                }
                agent = request.app.state.agent
                task = asyncio.create_task(run_agent(run_id, agent, query))
                run_store[run_id]["task"] = task
                search_mod._current_run_id = run_id

                return ChatResponse(
                    reply=last_msg.content or "Let me search for that...",
                    run_id=run_id,
                    tool_call=ToolCallInfo(
                        id=tc["id"],
                        name=tc["name"],
                        args=tc["args"],
                    ),
                )

    # -- Direct reply (no async tool) ---------------------------------------
    reply = ""
    if isinstance(last_msg, AIMessage):
        reply = last_msg.content or ""

    return ChatResponse(
        reply=reply or "I'm not sure how to help with that. Could you rephrase?",
    )
