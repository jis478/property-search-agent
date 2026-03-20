# Phase 3: LangGraph Agent - Research

**Researched:** 2026-02-20
**Domain:** LangGraph ReAct agent + Playwright MCP browser tools + domain.com.au scraping
**Confidence:** MEDIUM-HIGH (core APIs verified; domain.com.au URL params verified via OpenAPI gist; screenshot ToolMessage flow verified via source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Query interpretation
- All parameters are optional — even a bare query (e.g., "find properties") is valid; agent searches broadly
- No price range in query → search without a price filter (pass no price bounds to domain.com.au URL)
- Ambiguous location (e.g., "Richmond" — VIC or NSW) → pass suburb name as-is, let domain.com.au resolve it
- LLM interprets colloquial/shorthand input: "2br" → 2 bedrooms, "near CBD" → city-adjacent area, "500k" → $500,000 max price

#### Results shape and volume
- Always attempt all 3 pages regardless of sparse results — consistent, predictable behavior
- Return everything found across 3 pages (no cap) — ~75 listings maximum in practice
- Fields per listing (exactly these 6): `address`, `price`, `bedrooms`, `bathrooms`, `property_type`, `listing_url`
- Return type: `List[PropertyListing]` Pydantic models (not plain dicts) — typed, serializable for Phase 4 SSE

#### Error handling
- Full failures (bot detection, step limit, MCP crash) → raise Python exception with clear message
- Partial failure mid-run (e.g., page 1 ok, page 2 bot-detected) → return collected listings so far (partial results)
- Zero results → valid success, return empty list — not an exception
- Distinct exception classes per failure mode (for Phase 4 SSE to emit typed error events):
  - `BotDetectedError` — domain.com.au returned a challenge/captcha page
  - `StepLimitError` — agent hit the 10-step LangGraph limit without completing
  - `MCPError` — Playwright MCP subprocess crashed or became unresponsive

#### Scraping strategy
- **LLM reads screenshots** — take a screenshot of each search results page and have the LLM extract structured listing data visually (more robust to DOM changes than JSON-LD or CSS selectors)
- Minimum viable listing: `address` + `listing_url` must be present; all other fields may be `None`
- Missing price (e.g., "Price on application") → include listing with `price=None`
- Validation: best-effort — trust the LLM's extraction, no post-extraction numeric validation for Phase 3

### Claude's Discretion
- Exact LangGraph graph topology (node names, edge conditions)
- Screenshot prompt engineering for listing extraction
- How to construct domain.com.au search URLs from extracted parameters
- How to detect bot-challenge pages (visual cues in screenshot vs URL pattern)
- Exact Pydantic model field types (e.g., `price: str | None` vs `price: float | None`)
- Retry behavior within a single page (if screenshot is blank or unclear)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-01 | The agent uses a LangGraph ReAct loop with a defined step limit (≤ 10 steps by default) to prevent infinite loops | `create_react_agent(recursion_limit=10)` parameter verified; `GraphRecursionError` import path confirmed |
| AGNT-02 | The agent constructs domain.com.au search URLs from extracted query parameters — it never interacts with the search form | URL format research: path-based location + `bedrooms`, `bathrooms`, `price`, `ptype`, `page` query params |
| AGNT-03 | The agent extracts structured listing data from search results and returns it as a typed data structure (Pydantic model) | Pydantic v2 `BaseModel` with `field: str \| None = None` pattern; `response_format` on `create_react_agent` available |
| AGNT-04 | The agent detects bot-challenge pages and raises a recoverable error (not silently returning garbled data) | Bot detection via screenshot visual cues or URL pattern check; `BotDetectedError` raised from within tool or post-processing |
| SCRP-02 | The agent can scrape up to 3 pages of search results from a single query | 3-page loop: navigate to page URL (with `?page=1/2/3`), screenshot, extract — all within 10-step budget |
| SCRP-03 | The agent constructs domain.com.au search URLs directly from extracted parameters without using the search form | URL construction function: base path + query string from extracted params |
| SCRP-04 | When domain.com.au returns a CAPTCHA or bot-challenge page, the agent raises BotDetectedError rather than continuing | Bot detection logic: check for challenge keywords in screenshot text or URL mismatch |
| SCRP-05 | Scraped listing data is returned as a List[PropertyListing] Pydantic model with fields: address, price, bedrooms, bathrooms, property_type, listing_url | Pydantic v2 model definition confirmed; LLM extraction into JSON, then Pydantic parse |
</phase_requirements>

---

## Summary

Phase 3 builds a LangGraph ReAct agent that accepts natural-language property queries, navigates domain.com.au search result pages using Playwright MCP browser tools, and returns structured `List[PropertyListing]` Pydantic models. The agent is deliberately non-streaming — correctness is the only goal; streaming is Phase 4's concern.

The core technology stack is: `langgraph` 1.0.9 (to be installed) + `langchain-openai` 1.1.10 (to be installed) + existing `langchain-mcp-adapters` 0.2.1 + existing `pydantic` 2.12.5. The prebuilt `create_react_agent` from `langgraph.prebuilt` is the right choice despite the soft deprecation in LangGraph 1.0 — the stated replacement (`langchain.agents.create_agent`) is a higher-level wrapper that loses direct `recursion_limit` control needed for AGNT-01. Use `create_react_agent` with `recursion_limit=10`.

The most complex design challenge is the screenshot extraction flow: Playwright MCP's `browser_take_screenshot` tool returns image data as a LangChain standard image content block inside a `ToolMessage`; `langchain-mcp-adapters` 0.2+ handles this conversion automatically. GPT-4o is a vision model and will see the image when it appears in the message history as a content block. The LLM must be prompted to output a JSON array of listings from the screenshot — this JSON is then parsed into `List[PropertyListing]`.

**Primary recommendation:** Use `create_react_agent(model, tools, prompt=SYSTEM_PROMPT, recursion_limit=10)` from `langgraph.prebuilt`, with `browser_navigate` + `browser_take_screenshot` as the two primary tools, a separate Python post-processing step to parse the LLM's extracted JSON into Pydantic models, and custom exception classes defined before the agent is called.

---

## Standard Stack

### Core (to be installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | 1.0.9 | ReAct agent loop, graph execution, `GraphRecursionError` | The agent runtime — provides `create_react_agent`, step limiting, state management |
| `langchain-openai` | 1.1.10 | `ChatOpenAI` LLM binding for GPT-4o | Required to connect LangGraph to OpenAI; already implied by `openai` 2.17.0 in env |

### Already Installed
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `langchain-core` | 1.2.14 | Base message types, tool protocol | Already present (transitive dep) |
| `langchain-mcp-adapters` | 0.2.1 | Converts Playwright MCP tools to LangChain `BaseTool` | Phase 2 outcome; provides `load_mcp_tools` and image content block conversion |
| `pydantic` | 2.12.5 | `PropertyListing` model definition | Already present; v2 API required |
| `openai` | 2.17.0 | Underlying OpenAI client | Already present |

### Installation
```bash
pip install "langgraph>=1.0.9,<2" "langchain-openai>=1.1.10,<2"
```

Update `requirements.txt`:
```
langgraph>=1.0.9,<2
langchain-openai>=1.1.10,<2
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langgraph.prebuilt.create_react_agent` | `langchain.agents.create_agent` | New API is higher-level and loses direct `recursion_limit` parameter; stick with `create_react_agent` until it's removed in v2 |
| GPT-4o for vision extraction | GPT-4o-mini | 4o-mini vision is weaker for layout parsing; 4o is locked decision |
| Screenshot-based extraction | CSS selector / JSON-LD parsing | JSON-LD not always present; CSS selectors brittle; screenshot is locked decision |

---

## Architecture Patterns

### Recommended Project Structure
```
agent/
├── __init__.py
├── exceptions.py        # BotDetectedError, StepLimitError, MCPError
├── models.py            # PropertyListing Pydantic model
├── url_builder.py       # domain.com.au URL construction
├── prompts.py           # System prompt + screenshot extraction prompt
└── property_agent.py    # create_react_agent + ainvoke orchestration
```

The `agent/` directory already exists as an empty package. These files map cleanly to the phase requirements.

### Pattern 1: create_react_agent with Step Limit

**What:** Prebuilt ReAct loop with a hard step cap using `recursion_limit`.
**When to use:** Any agent that must not run indefinitely — catches infinite loops as `GraphRecursionError`.

```python
# Source: langgraph-prebuilt 1.0.8, PyPI + deepwiki research
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

agent = create_react_agent(
    model=llm,
    tools=mcp_tools,          # List[BaseTool] from load_mcp_tools()
    prompt=SYSTEM_PROMPT,     # str or SystemMessage
    recursion_limit=10,       # AGNT-01: hard cap
)

try:
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
except GraphRecursionError:
    raise StepLimitError("Agent exceeded 10-step limit")
```

**Key insight:** `recursion_limit=10` in `create_react_agent` sets the cap at construction time. Each navigate + screenshot pair costs ~2 steps. With 3 pages: 6 browser steps + query parsing + URL construction + response formatting = comfortably under 10 if the agent is efficient. The budget is tight — the system prompt must guide the agent to work in minimal steps.

### Pattern 2: Tool Selection — Minimal Tool Set

**What:** Pass only the tools the agent needs. Fewer tools = faster decisions.
**When to use:** Always with a step-limited agent.

The 22 Playwright MCP tools should be filtered to the minimum needed set:

```python
# Filter from app.state.mcp_tools to only what the agent needs
REQUIRED_TOOLS = {
    "browser_navigate",         # Navigate to constructed URL
    "browser_take_screenshot",  # Capture page as image
    "browser_wait_for",         # Optional: wait for page load
}

agent_tools = [t for t in all_mcp_tools if t.name in REQUIRED_TOOLS]
```

Giving the agent all 22 tools wastes tokens and risks wrong tool choices.

### Pattern 3: Screenshot Extraction Flow

**What:** The agent takes a screenshot; `langchain-mcp-adapters` 0.2 automatically converts the MCP image response to a LangChain standard image content block in the `ToolMessage`. GPT-4o (a vision model) sees the image in the next reasoning step and extracts listings as JSON.

**Flow:**
```
Agent calls browser_take_screenshot
  → MCP returns ImageContent(data=base64, mimeType="image/png")
  → langchain-mcp-adapters converts to ToolMessage(content=[{type:"image", base64:..., mime_type:"image/png"}])
  → GPT-4o's next turn sees the image content block
  → Agent outputs JSON array of listings in its final message
  → Python post-processing: parse JSON → List[PropertyListing]
```

**Source:** `langchain-mcp-adapters/langchain_mcp_adapters/tools.py` — `_convert_mcp_content_to_lc_block()` converts `ImageContent` to `create_image_block(base64=content.data, mime_type=content.mimeType)`.

### Pattern 4: Pydantic v2 Optional Fields

**What:** All listing fields except `address` and `listing_url` may be `None`.

```python
# Source: Pydantic v2 docs
from pydantic import BaseModel

class PropertyListing(BaseModel):
    address: str
    listing_url: str
    price: str | None = None          # "Price on application" → None
    bedrooms: int | None = None
    bathrooms: int | None = None
    property_type: str | None = None
```

**Why `price: str | None` not `float | None`:** Prices appear as "POA", "$1,200/week", "$450 pw" — treat as raw string. Numeric parsing is out of scope for Phase 3.

**Why `bedrooms: int | None`:** LLM extracts "3" → integer is safer than string for downstream consumers (Phase 4 SSE).

### Pattern 5: domain.com.au URL Construction

**What:** Build search URLs directly — never use the search form.

URL structure:
```
https://www.domain.com.au/rent/{suburb}-{state}-{postcode}/?{params}
```

Query parameters (source: OpenAPI gist reverse-engineered from domain.com.au):
| Parameter | Format | Example |
|-----------|--------|---------|
| `bedrooms` | `{min}-any` or `{min}-{max}` | `2-any` |
| `bathrooms` | `{min}-any` | `1-any` |
| `price` | `{min}-{max}` (weekly rent) | `500-2000` |
| `ptype` | property type slug(s) | `apartment-unit-flat` or `house` |
| `page` | integer (1-indexed) | `2` |

**Location format:** Suburb name lowercased, spaces replaced with `-`, followed by `-{state}-{postcode}`. If no postcode known, omit it. If only a suburb name: `richmond-vic` (let domain.com.au resolve).

```python
# Source: research from OpenAPI gist + scrapfly article
from urllib.parse import urlencode

PROPERTY_TYPE_MAP = {
    "apartment": "apartment-unit-flat",
    "unit": "apartment-unit-flat",
    "flat": "apartment-unit-flat",
    "house": "house",
    "townhouse": "townhouse",
}

def build_domain_url(
    suburb: str,
    page: int = 1,
    bedrooms_min: int | None = None,
    bathrooms_min: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    property_type: str | None = None,
) -> str:
    slug = suburb.lower().replace(" ", "-")
    base = f"https://www.domain.com.au/rent/{slug}/"
    params: dict[str, str] = {}
    if bedrooms_min:
        params["bedrooms"] = f"{bedrooms_min}-any"
    if bathrooms_min:
        params["bathrooms"] = f"{bathrooms_min}-any"
    if price_min or price_max:
        lo = price_min or 0
        hi = price_max or 99999
        params["price"] = f"{lo}-{hi}"
    if property_type:
        params["ptype"] = PROPERTY_TYPE_MAP.get(property_type.lower(), property_type)
    params["page"] = str(page)
    return f"{base}?{urlencode(params)}"
```

### Pattern 6: Exception Classes

```python
# agent/exceptions.py
class PropertyAgentError(Exception):
    """Base class for all agent errors."""

class BotDetectedError(PropertyAgentError):
    """domain.com.au returned a bot-challenge or CAPTCHA page."""

class StepLimitError(PropertyAgentError):
    """Agent hit the LangGraph recursion_limit without completing."""

class MCPError(PropertyAgentError):
    """Playwright MCP subprocess crashed or became unresponsive."""
```

### Anti-Patterns to Avoid

- **Giving the agent all 22 tools:** Slows down decision making, wastes tokens, risks wrong tool selection. Filter to 2-3 tools.
- **Streaming the agent output:** Phase 3 is non-streaming. Use `ainvoke`, not `astream`.
- **Parsing JSON inside the agent's system prompt as a tool call:** Let the agent output the JSON in its final assistant message; parse it in Python, not via tool.
- **Using `recursion_limit` only in config at call time:** Set it at construction time via `create_react_agent(recursion_limit=10)` — this is cleaner and avoids forgetting to pass config at each call site.
- **Not filtering `None` listings at parse time:** After LLM extraction, filter out any "listings" where both `address` and `listing_url` are missing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ReAct agent loop | Custom while-loop with tool dispatch | `create_react_agent` from `langgraph.prebuilt` | Handles tool call routing, message history, step limiting, error propagation |
| Step limit enforcement | Manual counter in agent state | `recursion_limit` parameter | LangGraph counts supersteps; manual counting races with graph execution |
| Screenshot → image flow | Custom MCP result parsing | `langchain-mcp-adapters` 0.2 automatic conversion | Already tested; converts `ImageContent` to standard content blocks automatically |
| Tool schema generation | Write JSON schema by hand | `@tool` decorator or existing MCP tools | MCP tools already have schemas from the server |
| GraphRecursionError handling | Try to detect stuck loops | `from langgraph.errors import GraphRecursionError` | Already raised by LangGraph when limit hit |

**Key insight:** The agent loop, step limiting, and screenshot → image conversion are all handled by the library stack. The only custom code is: URL construction, system prompts, JSON parsing, Pydantic model definition, and exception classes.

---

## Common Pitfalls

### Pitfall 1: Step Budget Exhaustion
**What goes wrong:** Agent uses up all 10 steps before scraping all 3 pages. It might spend steps on unnecessary tool calls (scrolling, clicking, form interaction).
**Why it happens:** The agent has access to tools it doesn't need and may use them.
**How to avoid:** Filter to exactly `{browser_navigate, browser_take_screenshot}` (+ optionally `browser_wait_for`). Write the system prompt to explicitly say: "Navigate directly to the URL, take a screenshot, extract, repeat. Do not use any other browser interactions."
**Warning signs:** Agent calling `browser_click`, `browser_fill_form`, or `browser_snapshot` instead of `browser_take_screenshot`.

### Pitfall 2: Screenshot Returns Blank/Loading Image
**What goes wrong:** `browser_take_screenshot` captures an empty page or loading spinner.
**Why it happens:** Dynamic JS sites (like domain.com.au) render content after the initial HTML load.
**How to avoid:** Include `browser_wait_for` in the tool set. System prompt should instruct: "After navigating, wait 2 seconds using browser_wait_for before taking a screenshot."
**Warning signs:** LLM reports "I see a blank page" or "Loading..." in the screenshot description.

### Pitfall 3: Bot Detection / CAPTCHA
**What goes wrong:** domain.com.au serves a bot challenge page instead of search results.
**Why it happens:** Headless Chromium without stealth mode is easily detected.
**How to avoid:** Use `--isolated` flag (already set in Phase 2 MCPManager) to avoid persistent state. The agent must detect this via screenshot — the challenge page looks visually different (CAPTCHA widget, "Verify you are human" text). Raise `BotDetectedError` immediately rather than returning garbled data.
**How to detect:** In the screenshot extraction prompt, instruct the LLM to output `{"bot_detected": true}` if it sees a challenge page instead of property listings.
**Warning signs:** LLM returns 0 listings repeatedly or extraction fails with unusual content.

### Pitfall 4: LLM Extracts Malformed JSON
**What goes wrong:** The LLM outputs JSON with trailing commas, unquoted keys, or markdown code fences around the JSON.
**Why it happens:** LLMs sometimes wrap JSON in ` ```json ``` ` blocks or make minor syntax errors.
**How to avoid:** Use `json.loads()` inside a try-except; strip code fence markers before parsing. Alternatively use `response_format` with a Pydantic model — but this adds complexity. For Phase 3, robust string preprocessing + `json.loads` is simpler.
**Warning signs:** `json.JSONDecodeError` at parse time.

### Pitfall 5: create_react_agent Deprecation Warning Noise
**What goes wrong:** `from langgraph.prebuilt import create_react_agent` emits a deprecation warning in LangGraph 1.0.x (deprecated in favor of `langchain.agents.create_agent`).
**Why it happens:** LangGraph 1.0 soft-deprecated `create_react_agent`; removal is planned for v2.0.
**How to avoid:** Use `create_react_agent` anyway for now (it still works and offers `recursion_limit` param). Suppress warning in tests with `warnings.filterwarnings("ignore", category=DeprecationWarning)` if needed. The GitHub issue #6404 confirms the deprecation message itself had a bug suggesting a non-existent `create_agent` — both APIs are valid as of Feb 2026.
**Warning signs:** `DeprecationWarning: create_react_agent is deprecated` in logs.

### Pitfall 6: domain.com.au URL Suburb Slug Format
**What goes wrong:** URL like `/rent/Richmond/` fails; correct slug is `/rent/richmond-vic/` or `/rent/richmond-vic-3121/`.
**Why it happens:** domain.com.au requires lowercase, hyphenated suburb slug in the URL path.
**How to avoid:** URL builder lowercases and replaces spaces with hyphens. Without state/postcode, domain.com.au will often still resolve correctly. The agent's system prompt should instruct the LLM to include state code when it can be inferred.
**Warning signs:** 404 or redirect to homepage.

### Pitfall 7: GraphRecursionError Not Raised When Last Message is ToolMessage
**What goes wrong:** There is a reported bug (LangGraph issue #5548, July 2025) where `GraphRecursionError` is not raised when the last message in state is a `ToolMessage` — the loop may silently complete without the expected exception.
**Why it happens:** Edge case in LangGraph's stop condition check.
**How to avoid:** Also check the final result for completeness (verify all 3 pages were attempted). If the result looks incomplete and no exception was raised, check if the step count was hit. This may be fixed in 1.0.9 — validate in tests.
**Warning signs:** Agent completes with fewer than expected pages scraped, no exception raised.

---

## Code Examples

### Agent Initialization
```python
# Source: langgraph.prebuilt API (deepwiki research, verified against PyPI 1.0.8)
from langgraph.prebuilt import create_react_agent
from langgraph.errors import GraphRecursionError
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools  # already in project

from agent.exceptions import StepLimitError, MCPError
from agent.prompts import SYSTEM_PROMPT

REQUIRED_TOOLS = {"browser_navigate", "browser_take_screenshot", "browser_wait_for"}

async def build_agent(mcp_tools: list) -> object:
    """Build the property search agent using app.state.mcp_tools."""
    filtered_tools = [t for t in mcp_tools if t.name in REQUIRED_TOOLS]
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    return create_react_agent(
        model=llm,
        tools=filtered_tools,
        prompt=SYSTEM_PROMPT,
        recursion_limit=10,  # AGNT-01
    )
```

### Agent Invocation
```python
# Source: LangGraph ainvoke pattern, verified
async def search_properties(
    agent, query: str
) -> list[PropertyListing]:
    from langgraph.errors import GraphRecursionError
    from agent.exceptions import StepLimitError

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": query}]}
        )
    except GraphRecursionError:
        raise StepLimitError(
            f"Agent exceeded 10-step limit for query: {query!r}"
        )

    # Extract final assistant message and parse listings
    final_message = result["messages"][-1]
    return parse_listings_from_message(final_message.content)
```

### Pydantic Model
```python
# Source: Pydantic v2 docs — verified with pydantic 2.12.5 installed
from pydantic import BaseModel

class PropertyListing(BaseModel):
    """A single property listing from domain.com.au."""
    address: str
    listing_url: str
    price: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    property_type: str | None = None

    def is_valid(self) -> bool:
        """Minimum viable listing requires address and URL."""
        return bool(self.address and self.listing_url)
```

### Exception Classes
```python
# agent/exceptions.py
class PropertyAgentError(Exception):
    """Base class for all property agent errors."""

class BotDetectedError(PropertyAgentError):
    """domain.com.au returned a bot-challenge or CAPTCHA page."""

class StepLimitError(PropertyAgentError):
    """Agent hit the LangGraph recursion_limit without completing."""

class MCPError(PropertyAgentError):
    """Playwright MCP subprocess crashed or became unresponsive."""
```

### System Prompt (Draft)
```python
# agent/prompts.py — Claude's Discretion area
SYSTEM_PROMPT = """You are a property search assistant that finds rental listings on domain.com.au.

You will receive a search query. Your job:
1. Extract search parameters from the query (suburb/location, bedrooms, price range, property type)
2. I will construct the domain.com.au search URL for you (you receive it in the query)
3. Navigate to the URL using browser_navigate
4. Wait 2 seconds for the page to load using browser_wait_for
5. Take a screenshot using browser_take_screenshot
6. Extract ALL visible property listings from the screenshot as a JSON array
7. Repeat for pages 2 and 3 (append ?page=2 and ?page=3 to the URL)
8. Return all collected listings

IMPORTANT: If you see a CAPTCHA or "verify you are human" challenge page, output:
{"bot_detected": true, "listings": []}

For each listing, extract:
- address: full street address
- listing_url: the URL of the listing (from the href you can see or construct)
- price: displayed price as text (e.g., "$450 pw") or null if not shown
- bedrooms: integer or null
- bathrooms: integer or null
- property_type: "apartment", "house", "townhouse", etc. or null

Output format: {"listings": [...], "bot_detected": false}

Only use browser_navigate, browser_take_screenshot, and browser_wait_for.
Do NOT use browser_click, browser_fill_form, or any other tools.
"""
```

**Note:** The system prompt above is a starting draft — prompt engineering is in Claude's Discretion. The key constraints are: (1) output format as JSON, (2) bot detection signal, (3) explicit tool restriction, (4) page iteration instructions.

### URL Builder
```python
# agent/url_builder.py
from urllib.parse import urlencode

PROPERTY_TYPE_MAP = {
    "apartment": "apartment-unit-flat",
    "unit": "apartment-unit-flat",
    "flat": "apartment-unit-flat",
    "house": "house",
    "townhouse": "townhouse",
    "studio": "studio",
}

def build_search_url(
    suburb: str,
    page: int = 1,
    bedrooms_min: int | None = None,
    bathrooms_min: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    property_type: str | None = None,
) -> str:
    """Construct a domain.com.au rental search URL.

    Source: URL parameters reverse-engineered from domain.com.au OpenAPI spec
    (gist.github.com/0xdevalias/18e666bc319b2e08f90e52bb5cb53538)

    Suburb slug format: lowercase, spaces → hyphens, optionally append state/postcode
    Example: "Richmond VIC 3121" → "richmond-vic-3121"
    """
    slug = suburb.lower().replace(" ", "-")
    base = f"https://www.domain.com.au/rent/{slug}/"
    params: dict[str, str] = {}
    if bedrooms_min is not None:
        params["bedrooms"] = f"{bedrooms_min}-any"
    if bathrooms_min is not None:
        params["bathrooms"] = f"{bathrooms_min}-any"
    if price_min is not None or price_max is not None:
        lo = price_min or 0
        hi = price_max or 99999
        params["price"] = f"{lo}-{hi}"
    if property_type:
        params["ptype"] = PROPERTY_TYPE_MAP.get(property_type.lower(), property_type.lower())
    params["page"] = str(page)
    return f"{base}?{urlencode(params)}"
```

### JSON Parsing with Robustness
```python
import json
import re

def parse_listings_from_message(content: str | list) -> list[PropertyListing]:
    """Parse LLM-extracted listings from final assistant message."""
    # Handle multimodal content (list of blocks)
    if isinstance(content, list):
        text = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    else:
        text = content

    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object from surrounding text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group())

    if data.get("bot_detected"):
        from agent.exceptions import BotDetectedError
        raise BotDetectedError("domain.com.au returned a bot-challenge page")

    raw_listings = data.get("listings", [])
    result = []
    for item in raw_listings:
        try:
            listing = PropertyListing(**item)
            if listing.is_valid():
                result.append(listing)
        except Exception:
            pass  # Skip malformed listings
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `AgentExecutor` (LangChain) | `create_react_agent` (LangGraph) | 2024 | More reliable tool call routing, proper state management |
| `langgraph.prebuilt.create_react_agent` | `langchain.agents.create_agent` (soft deprecation) | Oct 2025 (LangGraph 1.0) | Deprecated but not removed; use `create_react_agent` for Phase 3 (removal in v2.0) |
| Manual image passing to LLM | Automatic standard content blocks via `langchain-mcp-adapters` 0.2 | ~late 2024 | Screenshot images flow automatically; no manual base64 encoding needed |
| `LangGraph 0.x` | `LangGraph 1.0.x` (stable API) | Oct 2025 | No breaking changes; Python 3.10+ required |

**Deprecated/outdated:**
- `AgentExecutor`: Removed/deprecated in LangChain 1.0; do not use.
- `from langchain.agents import create_react_agent` (old LangChain): Different from `langgraph.prebuilt.create_react_agent`; not the same function.

---

## Open Questions

1. **domain.com.au URL slug for suburb-only (no state/postcode)**
   - What we know: The URL path uses `suburb-state-postcode` or `suburb-state` format
   - What's unclear: Whether `richmond-vic` works without postcode when resolving ambiguous suburbs
   - Recommendation: Always include state code if determinable from query; the LLM should extract state from "Richmond VIC" naturally. Pass suburb-as-is if only suburb name given (let domain.com.au resolve).

2. **Bot detection reliability in WSL2 headless Chromium**
   - What we know: Headless Chromium is detectable; `--isolated` flag avoids persistent cookies
   - What's unclear: Whether domain.com.au will block the test environment; frequency of bot challenges
   - Recommendation: Implement `BotDetectedError` detection conservatively, test manually on a few queries first. If bot detection is frequent, consider `--no-sandbox --isolated` flags already in use.

3. **Listing URL extraction from screenshot**
   - What we know: The agent sees the page visually; individual listing URLs are not in the screenshot URL bar
   - What's unclear: Whether the LLM can reliably extract `listing_url` from what it sees (listing cards typically show address + brief details, URL may not be visible)
   - Recommendation: For `listing_url`, either: (a) instruct LLM to construct it from listing ID if visible (domain.com.au listing URLs follow pattern `https://www.domain.com.au/{id}`), or (b) use `browser_snapshot` (accessibility tree) which may expose href attributes. This is a key risk item.

4. **Step budget for 3 pages**
   - What we know: 3 pages × (navigate + wait + screenshot) = 9 tool calls = ~9-10 supersteps in LangGraph
   - What's unclear: Whether LangGraph counts each tool call as 1 superstep or 2 (agent + tools nodes)
   - Recommendation: Test with a simple 3-page scrape early. If budget is tight, consider increasing `recursion_limit` to 15 and updating AGNT-01 requirement interpretation (the requirement says "≤ 10 steps by default" — a configurable default is acceptable).

---

## Sources

### Primary (HIGH confidence)
- `langgraph-prebuilt` 1.0.8 PyPI + deepwiki research — `create_react_agent` function signature, `recursion_limit` parameter, return type
- `langchain-mcp-adapters` GitHub source `tools.py` — `_convert_mcp_content_to_lc_block()` image conversion confirmed
- `langchain-openai` 1.1.10 PyPI — current version confirmed Feb 17, 2026
- `langgraph` 1.0.9 PyPI — current version confirmed Feb 19, 2026
- Pydantic v2 docs — `field: str | None = None` optional field pattern
- `langchain.errors.GraphRecursionError` — import path confirmed via baihezi.com LangGraph errors mirror

### Secondary (MEDIUM confidence)
- [LangGraph v1 migration docs](https://docs.langchain.com/oss/python/migrate/langgraph-v1) — deprecation of `create_react_agent` in favor of `langchain.agents.create_agent`; soft deprecation confirmed
- [LangGraph errors reference](https://www.baihezi.com/mirrors/langgraph/reference/errors/index.html) — `from langgraph.errors import GraphRecursionError` confirmed
- [LangChain MCP Adapters 0.2.0 changelog](https://changelog.langchain.com/announcements/langchain-mcp-adapters-0-2-0) — multimodal tool support confirmed
- [OpenAPI gist for domain.com.au](https://gist.github.com/0xdevalias/18e666bc319b2e08f90e52bb5cb53538) — URL parameters `bedrooms`, `bathrooms`, `price`, `ptype`, `page` confirmed
- [scrapfly.io domain.com.au article](https://scrapfly.io/blog/posts/how-to-scrape-domain-com-au-real-estate-property-data) — pagination `?page=N` confirmed; suburb slug in path confirmed

### Tertiary (LOW confidence)
- domain.com.au URL parameter format: `bedrooms=2-any` format inferred from OpenAPI gist reverse-engineering — needs validation by manually checking a domain.com.au search URL in a browser

---

## Metadata

**Confidence breakdown:**
- Standard stack (LangGraph, langchain-openai): HIGH — current versions confirmed via PyPI
- create_react_agent API: HIGH — function signature verified via multiple sources
- Screenshot image flow: HIGH — source code of `langchain-mcp-adapters` examined
- domain.com.au URL format: MEDIUM — core structure confirmed (path-based location, `?page=N`); exact parameter names inferred from OpenAPI gist, need browser validation
- Architecture patterns: MEDIUM — patterns based on verified APIs, specific prompt engineering is Claude's Discretion
- Pitfalls: MEDIUM — most from documented issues + known web scraping patterns

**Research date:** 2026-02-20
**Valid until:** 2026-03-06 (14 days — LangGraph is stable 1.0 series, but domain.com.au URL format may change)
