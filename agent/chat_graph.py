"""LangGraph StateGraph workflow for conversational chat with tool calling.

Architecture
------------
                ┌──────────┐
    START ────▶ │  agent   │ (LLM + tools)
                └────┬─────┘
                     │
              ┌──────┴──────┐
              ▼             ▼             ▼
           no tool     async tool     sync tool
           calls     (search_props)   (future)
              │             │             │
             END           END      ┌─────┴─────┐
                      (run_id set)  │ sync_tools │
                                    └─────┬─────┘
                                          │
                                     back to agent

- **Async tools** (e.g. search_properties): The graph exits immediately.
  The API layer detects the pending tool_call on the last AIMessage and
  kicks off a background task + SSE stream.
- **Sync tools** (future): Executed inside the graph, result loops back
  to the agent node so the LLM can produce a final answer.
"""
from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

ASYNC_TOOLS = frozenset({"search_properties"})


@tool
def search_properties(
    query: str,
    school: str | None = None,
    max_distance_meters: int | None = None,
) -> str:
    """Search for property listings.

    Use when the user asks to find, look for, or search for rental/sale
    properties, apartments, houses, units, townhouses, etc.

    When the user mentions a school and walking distance (e.g. "within 500m of
    Richmond Primary School"), provide school name/address and max_distance_meters.
    Results will be filtered to walking distance and include distance_to_school.

    Do NOT call for follow-up questions about already-retrieved listings.

    Args:
        query: Concise English search description,
               e.g. "2 bedroom apartment in Richmond VIC under $600 per week"
        school: School name or address for distance filter (e.g. "Richmond Primary School, VIC")
        max_distance_meters: Max walking distance in meters (e.g. 500 for 500m)
    """
    return ""


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = (
    "You are a helpful property-search assistant. "
    "Reply in the same language the user is using (English, Korean, etc.). "
    "You have tools available — use them when appropriate. "
    "When the user asks for properties within walking distance of a school "
    "(e.g. 'within 500m of Richmond Primary School', '학교 500m 이내'), "
    "set school to the school name/address and max_distance_meters (e.g. 500). "
    "For follow-up questions about previously searched results "
    "(visible as ToolMessage in the conversation), answer directly "
    "from that data without calling search_properties again."
)


def build_chat_graph(sync_tools: list | None = None):
    """Build and compile the chat orchestration graph.

    Args:
        sync_tools: Optional list of additional LangChain tool objects that
                    execute quickly (< 1 s). They will be run inside the
                    graph and their results fed back to the LLM.

    Returns:
        A compiled LangGraph that accepts ``{"messages": [...]}`` and
        returns the updated messages list.
    """
    all_tools: list = [search_properties]
    sync_tool_map: dict = {}

    if sync_tools:
        all_tools.extend(sync_tools)
        for t in sync_tools:
            sync_tool_map[t.name] = t

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(all_tools)

    # -- nodes ---------------------------------------------------------------

    def agent_node(state: ChatState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    def sync_tools_node(state: ChatState) -> dict:
        last: AIMessage = state["messages"][-1]
        results: list[ToolMessage] = []
        for tc in last.tool_calls:
            fn = sync_tool_map.get(tc["name"])
            if fn:
                output = fn.invoke(tc["args"])
            else:
                output = f"Error: unknown tool '{tc['name']}'"
            results.append(
                ToolMessage(content=str(output), tool_call_id=tc["id"], name=tc["name"])
            )
        return {"messages": results}

    # -- routing -------------------------------------------------------------

    def route_after_agent(state: ChatState) -> str:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return END
        for tc in last.tool_calls:
            if tc["name"] in ASYNC_TOOLS:
                return "async_exit"
        return "sync_tools"

    # -- graph assembly ------------------------------------------------------

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent_node)
    graph.add_node("sync_tools", sync_tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"async_exit": END, "sync_tools": "sync_tools", END: END},
    )
    graph.add_edge("sync_tools", "agent")

    return graph.compile()
