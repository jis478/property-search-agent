# Phase 3: LangGraph Agent - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a LangGraph ReAct agent that accepts natural-language property queries, extracts parameters, constructs domain.com.au search URLs, navigates up to 3 pages using Playwright MCP browser tools, and returns structured property listings as Pydantic models — no streaming, correctness verified before Phase 4 adds SSE.

</domain>

<decisions>
## Implementation Decisions

### Query interpretation
- All parameters are optional — even a bare query (e.g., "find properties") is valid; agent searches broadly
- No price range in query → search without a price filter (pass no price bounds to domain.com.au URL)
- Ambiguous location (e.g., "Richmond" — VIC or NSW) → pass suburb name as-is, let domain.com.au resolve it
- LLM interprets colloquial/shorthand input: "2br" → 2 bedrooms, "near CBD" → city-adjacent area, "500k" → $500,000 max price

### Results shape and volume
- Always attempt all 3 pages regardless of sparse results — consistent, predictable behavior
- Return everything found across 3 pages (no cap) — ~75 listings maximum in practice
- Fields per listing (exactly these 6): `address`, `price`, `bedrooms`, `bathrooms`, `property_type`, `listing_url`
- Return type: `List[PropertyListing]` Pydantic models (not plain dicts) — typed, serializable for Phase 4 SSE

### Error handling
- Full failures (bot detection, step limit, MCP crash) → raise Python exception with clear message
- Partial failure mid-run (e.g., page 1 ok, page 2 bot-detected) → return collected listings so far (partial results)
- Zero results → valid success, return empty list — not an exception
- Distinct exception classes per failure mode (for Phase 4 SSE to emit typed error events):
  - `BotDetectedError` — domain.com.au returned a challenge/captcha page
  - `StepLimitError` — agent hit the LangGraph recursion limit (default 15 steps — LangGraph counts reasoning supersteps as well as tool calls, so 10 is insufficient for 3-page searches)
  - `MCPError` — Playwright MCP subprocess crashed or became unresponsive

### Scraping strategy
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

</decisions>

<specifics>
## Specific Ideas

- Screenshot-based extraction is intentional — chosen for robustness over JSON-LD parsing. The LLM should be prompted to extract a JSON array of listings from what it sees on the page.
- Partial results on mid-run failure should include a metadata flag so Phase 4 can signal "incomplete results" to the frontend

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-langgraph-agent*
*Context gathered: 2026-02-20*
