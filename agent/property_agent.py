"""LangGraph ReAct agent construction and invocation for property search.

build_agent(mcp_tools):
    Constructs a LangGraph ReAct agent with GPT-4o, filtering the provided MCP
    tools to only the three browser tools required for domain.com.au scraping.
    Returns the compiled graph; recursion_limit is enforced at invocation time.

search_properties(agent, query):
    Async function that invokes the agent with a user query and returns a
    list of PropertyListing objects.

Error contract:
    - GraphRecursionError is caught and re-raised as StepLimitError.
    - BotDetectedError propagates naturally from parse_listings_from_message
      (raised when bot detection triggers with no listings collected).
    - Partial results (bot_detected=True but some listings collected) are
      returned as a list — not an error — per the CONTEXT.md locked decision.
"""
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage

from agent.prompts import SYSTEM_PROMPT

# Only these three tools are permitted. The Playwright MCP server exposes ~22
# tools; we filter here so the agent cannot waste its step budget on others.
REQUIRED_TOOLS = {"browser_navigate", "browser_take_screenshot", "browser_wait_for"}

# recursion_limit=15 is the practical minimum for 3-page scraping.
# LangGraph counts every reasoning superstep (not just tool calls):
#   3 pages × (navigate + wait + screenshot) = 9 tool calls
#   Plus one reasoning step between each tool pair = ~12 supersteps minimum.
# The AGNT-01 requirement ("prevent infinite loops, keep browser calls ≤ 10")
# refers to browser tool calls, not total supersteps. 15 supersteps gives
# room for three full pages without triggering the limit on a clean run.
_RECURSION_LIMIT = 15


def _move_tool_images_to_user(state: dict) -> dict:
    """OpenAI only allows images in 'user' role messages, not 'tool' messages.

    langchain-mcp-adapters puts browser_take_screenshot results (images) inside
    ToolMessages. This pre_model_hook lifts those image blocks out into a following
    HumanMessage so GPT-4o can see them without the API rejecting the request.

    pre_model_hook signature: takes state dict, returns dict with 'llm_input_messages'.
    """
    messages = state.get("messages", [])
    result = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and isinstance(msg.content, list):
            image_blocks = [b for b in msg.content if isinstance(b, dict) and b.get("type") == "image"]
            text_blocks = [b for b in msg.content if not (isinstance(b, dict) and b.get("type") == "image")]
            if image_blocks:
                result.append(ToolMessage(
                    content=text_blocks if text_blocks else "Screenshot taken.",
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                ))
                result.append(HumanMessage(content=image_blocks))
                continue
        result.append(msg)
    return {"llm_input_messages": result}


def build_agent(mcp_tools: list):
    """Construct a LangGraph ReAct agent configured for property scraping.

    Filters mcp_tools to only the three required browser tools, then builds
    a create_react_agent with GPT-4o and the domain.com.au system prompt.

    Args:
        mcp_tools: List of LangChain tool objects from the MCP adapter.
                   Typically sourced from app.state.mcp_tools.

    Returns:
        A compiled LangGraph graph (CompiledGraph) ready for ainvoke.
    """
    agent_tools = [t for t in mcp_tools if t.name in REQUIRED_TOOLS]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    return create_react_agent(
        model=llm,
        tools=agent_tools,
        prompt=SYSTEM_PROMPT,
        pre_model_hook=_move_tool_images_to_user,
    )


async def search_properties(agent, query: str) -> list:
    """Invoke the property agent and return extracted property listings.

    Calls the agent with a user query, extracts the final message from the
    result, and delegates JSON parsing and bot detection to
    parse_listings_from_message.

    Args:
        agent: A compiled LangGraph graph returned by build_agent().
        query: Natural language query or a pre-built domain.com.au URL string.

    Returns:
        List of PropertyListing objects. May be empty if agent finds no results.
        May be a partial list if bot detection triggered mid-run but some
        listings were collected on earlier pages.

    Raises:
        StepLimitError: When the agent exceeds the recursion limit.
        BotDetectedError: When bot detection triggers with no listings collected.
    """
    from langgraph.errors import GraphRecursionError
    from agent.exceptions import StepLimitError
    from agent.url_builder import parse_listings_from_message

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": query}]},
            config={"recursion_limit": _RECURSION_LIMIT},
        )
    except GraphRecursionError as exc:
        raise StepLimitError(
            f"Agent exceeded recursion_limit={_RECURSION_LIMIT} without completing."
        ) from exc

    final_message = result["messages"][-1]
    return parse_listings_from_message(final_message.content)
