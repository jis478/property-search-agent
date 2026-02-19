# Feature Research

**Domain:** LangGraph ReAct agent — natural-language property search over domain.com.au
**Researched:** 2026-02-19
**Confidence:** MEDIUM (training knowledge; verify domain.com.au URL structure and bot behaviour during implementation)

---

## domain.com.au Search URL Structure

Domain.com.au uses a path-first + query-parameter pattern:

```
https://www.domain.com.au/{intent}/{suburb}-{state}-{postcode}/
  ?bedrooms={min}-{max}
  &bathrooms={min}-{max}
  &price={min}-{max}
  &propertyTypes={type1},{type2}
  &excludeunderoffer=1
  &page={n}
```

**Intent segment:** `sale`, `rent`, `sold`, `lease`

**Suburb segment:** kebab-case, e.g. `surry-hills-nsw-2010`, `brunswick-vic-3056`

| Parameter | Values | Notes |
|-----------|--------|-------|
| `bedrooms` | `{min}-{max}` e.g. `2-4` | Use `0` for studios |
| `bathrooms` | `{min}-{max}` e.g. `1-2` | |
| `price` | `{min}-{max}` e.g. `500000-900000` | Rent uses weekly figures |
| `propertyTypes` | `house`, `apartment`, `townhouse`, `villa`, `land` | Comma-separated |
| `excludeunderoffer` | `1` | Hides under-offer listings |
| `page` | integer | ~25 results per page |
| `sort` | `price-asc`, `price-desc`, `date-desc` | |

**Key agent implication:** Construct URLs directly rather than filling the search form — URL construction is far more reliable than form interaction.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity |
|---------|--------------|------------|
| Natural-language query input | Core product promise | LOW |
| Live streaming of agent steps | Without this, 15-30s wait feels broken | MEDIUM |
| Structured listing cards | Users scan visually, not raw JSON | MEDIUM |
| Clickable listing URLs | Users need to open domain.com.au to act | LOW |
| Price display | Every property tool shows price prominently | LOW |
| Bedroom and bathroom count | Standard property metadata | LOW |
| Property type label | House vs apartment vs townhouse | LOW |
| Suburb / address | Location is the #1 property criterion | LOW |
| Error state when search fails | Agent may fail or hit bot detection | MEDIUM |
| "No results found" state | Distinguish from agent failure | LOW |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity |
|---------|-------------------|------------|
| Agent "thinking" display | Transparency builds trust; users see reasoning | MEDIUM |
| Natural-language interpretation feedback | "Searching: 3 beds, Brunswick, $600k-$800k" | LOW |
| Multi-page result aggregation | Fetch pages 1-3; cap at ~75 listings | MEDIUM |
| Land size extraction | Meaningful for houses | MEDIUM |
| Photo thumbnails | Visual scanning is faster | MEDIUM |
| Result count indicator | "Found 47 listings across 2 pages" | LOW |
| Copy results as markdown/JSON | Power user clipboard feature | LOW |
| Days on market | Listing freshness matters to buyers | MEDIUM |

### Anti-Features (Deliberately NOT Build for v1)

| Feature | Why Problematic |
|---------|-----------------|
| User authentication / accounts | Auth complexity with zero core value — local dev tool |
| Comparison view / side-by-side | Distracts from core reliability work |
| Price history charts | Requires separate API — not available on listing pages |
| Email/push alerts | Transforms scraper into monitoring service |
| Map view | Requires mapping library + geocoding |
| Concurrent multi-suburb search | Race conditions with single browser context |
| Full per-listing detail scraping for all results | 25x request multiplication, high bot-detection risk |
| Real-time auto-refresh | Continuous Playwright sessions trigger bot detection |
| Voice input | Build step complexity for marginal gain |

---

## Feature Dependencies

```
[Natural-language query input]
    └──requires──> [LLM parameter extraction]
                       └──requires──> [URL construction logic]
                                          └──requires──> [Playwright navigation]
                                                             └──requires──> [HTML extraction]
                                                                                └──requires──> [Listing cards]

[Streaming agent steps]
    └──requires──> [SSE endpoint in FastAPI]
                       └──requires──> [LangGraph .astream_events()]

[Multi-page aggregation] ──conflicts──> [Fast response time]
[Photo thumbnails] ──requires──> [Image URL extraction from search results page]
```

**Key risk:** Suburb-to-path-segment mapping (e.g. "Fitzroy" → `fitzroy-vic-3065`) requires either a lookup table or LLM knowledge of Australian postcodes — this is the most failure-prone step.

---

## UI Streaming Patterns for Agent Tools

### Recommended Step Display

```
[Thinking indicator — pulsing dot]

Step 1   Interpreting your request...
         → Searching: 3 bedrooms, Fitzroy VIC, $600k-$800k, House

Step 2   Navigating to domain.com.au...
         → https://www.domain.com.au/sale/fitzroy-vic-3065/?bedrooms=3-3&price=600000-800000

Step 3   Extracting listings from page 1...
         → Found 18 listings

Step 4   Fetching page 2...
         → Found 12 more listings

[Results appear below]
```

**Key UX decisions:**
1. Plain-English tool labels — "Navigating to domain.com.au" not `browser_navigate`
2. Show the URL — builds trust
3. Show intermediate counts — maintains engagement during wait
4. Collapse tool details by default; expand on click
5. Clear completion signal — "Search complete — 30 listings found"

### SSE Event Types to Emit

| Event Type | When | Frontend Action |
|------------|------|-----------------|
| `agent_start` | Request begins | Show spinner, clear previous results |
| `thinking` | LLM reasoning tokens (streamed) | Update thinking text area |
| `tool_call` | Agent calls a tool | Add step card with friendly label + input summary |
| `tool_result` | Tool returns | Update step card with result summary |
| `listing` | One listing extracted | Append listing card |
| `agent_end` | Agent finishes | Hide spinner, show completion banner |
| `error` | Any failure | Show error message, hide spinner |

---

## Playwright Scraping Reliability

### Brittle Patterns to Avoid

1. **CSS selector fragility** — Domain.com.au redesigns frontend; class-name selectors break silently. Use `data-testid` or JSON-LD.
2. **Immediate extraction after goto** — React-rendered pages need `wait_for_selector()` before extraction.
3. **Bot detection** — Domain.com.au uses Cloudflare. Realistic user agents + delays reduce (not eliminate) risk.
4. **Price format variance** — "$750,000", "POA", "Contact Agent", "$650 per week" — normalise or pass as raw strings.

### Reliability Patterns That Work

| Pattern | What It Solves |
|---------|---------------|
| JSON-LD extraction | Fragile CSS selectors — `<script type="application/ld+json">` has structured data |
| `wait_for_selector()` with timeout | Dynamic content not yet rendered |
| `asyncio.sleep(1-2)` between pages | Bot detection rate limiting |
| Realistic user-agent header | Headless browser fingerprinting |
| URL construction (not form fill) | Form interaction brittleness — skip the search box entirely |
| Extract from search results page | Avoids 25 additional per-listing page loads |

---

## MVP Definition

### Launch With (v1)

- [ ] Natural-language query input field + submit button
- [ ] LLM parameter extraction (suburb, price, beds, property type)
- [ ] domain.com.au URL construction from extracted parameters
- [ ] Playwright navigation + search-results-page HTML extraction
- [ ] Listing data: address, price, bedrooms, bathrooms, property type, listing URL
- [ ] SSE streaming of agent steps
- [ ] Plain-English step display (with URL shown)
- [ ] Structured listing cards
- [ ] Error and zero-results states
- [ ] Interpretation feedback ("Searching for: 3br houses in Fitzroy, $600k-$800k")

### Add After Validation (v1.x)

- [ ] Photo thumbnails (when confirmed extractable without extra requests)
- [ ] Multi-page aggregation (up to 3 pages)
- [ ] Result count indicator
- [ ] Land size extraction
- [ ] Copy results as JSON/markdown

### Future (v2+)

- Map view, saved searches, days on market, distance/drive time

---

## Feature Prioritization

| Feature | User Value | Cost | Priority |
|---------|------------|------|----------|
| Natural-language input | HIGH | LOW | P1 |
| SSE streaming | HIGH | MEDIUM | P1 |
| Listing cards (address, price, beds, baths, URL) | HIGH | MEDIUM | P1 |
| LLM parameter extraction + URL construction | HIGH | MEDIUM | P1 |
| Agent step display | HIGH | LOW | P1 |
| Error / zero-results states | HIGH | LOW | P1 |
| Interpretation feedback | MEDIUM | LOW | P1 |
| Photo thumbnails | MEDIUM | MEDIUM | P2 |
| Multi-page aggregation | MEDIUM | MEDIUM | P2 |
| Result count | LOW | LOW | P2 |
| Land size | MEDIUM | LOW | P2 |
| Map view | HIGH | HIGH | P3 |

---

*Feature research for: LangGraph ReAct property search agent (domain.com.au)*
*Researched: 2026-02-19*
