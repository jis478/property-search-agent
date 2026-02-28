---
phase: 03-langgraph-agent
plan: 01
subsystem: agent
tags: [pydantic, url-builder, parser, tdd, domain-com-au, langgraph]

# Dependency graph
requires:
  - phase: 02-mcp-integration
    provides: agent/exceptions.py with BotDetectedError — deferred import in parse_listings_from_message
provides:
  - PropertyListing Pydantic v2 model (address+listing_url required, rest optional)
  - build_search_url: domain.com.au /rent/ URL construction with all filter params
  - parse_listings_from_message: LLM output -> List[PropertyListing] with full edge-case handling
  - PROPERTY_TYPE_MAP: colloquial name -> domain.com.au ptype value mapping
affects:
  - 03-03 (property_agent.py calls parse_listings_from_message — partial-results contract)
  - 04 (Phase 4 SSE endpoints import PropertyListing for JSON serialization)

# Tech tracking
tech-stack:
  added: [pydantic v2 BaseModel]
  patterns:
    - TDD red-green with deferred import for cross-plan dependency
    - Partial-results contract: bot_detected=True + non-empty listings returns data (not raises)
    - Regex fallback JSON parsing for embedded content

key-files:
  created:
    - agent/models.py
    - agent/url_builder.py
    - tests/test_url_builder.py
    - tests/test_parser.py
  modified: []

key-decisions:
  - "Deferred import of BotDetectedError inside parse_listings_from_message body — avoids ImportError when agent/exceptions.py from Plan 02 hasn't been committed yet at test collection time"
  - "Partial-results contract: bot_detected=True + non-empty listings returns collected listings (not raise) — per CONTEXT.md locked decision for mid-run failure scenarios"
  - "price field is str|None (not float) — preserves display format e.g. '$450 pw', 'Price on application'"
  - "is_valid() checks both address AND listing_url are non-empty — minimum viable listing definition"

patterns-established:
  - "PropertyListing.is_valid(): minimum viable listing requires both address and listing_url"
  - "parse_listings_from_message owns all JSON parsing and bot detection — no inline parsing in callers"
  - "urlencode for query string construction — handles special characters and encoding"

requirements-completed: [AGNT-02, AGNT-03, SCRP-03, SCRP-05]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 3 Plan 01: URL Builder and Listing Parser Summary

**PropertyListing Pydantic model + domain.com.au URL builder + LLM-output parser with partial-results contract and bot detection, TDD'd with 31 tests (14 URL builder, 17 parser/model)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T03:26:55Z
- **Completed:** 2026-02-28T03:29:12Z
- **Tasks:** 2 (RED commit + GREEN commit)
- **Files modified:** 4

## Accomplishments
- PropertyListing Pydantic v2 model with 6 fields (address+listing_url required, rest optional) and is_valid() method
- build_search_url constructs valid domain.com.au /rent/ URLs with bedrooms, bathrooms, price, property_type, page params
- parse_listings_from_message handles plain JSON, markdown fences, multimodal content blocks, regex fallback, and partial-results contract
- 31 new tests covering all specified behavior cases; full suite (39 tests) passes in 1.95s

## Task Commits

Each task was committed atomically:

1. **RED — Failing tests for URL builder and parser** - `7df0bab` (test)
2. **GREEN — PropertyListing model and URL builder implementation** - `a089470` (feat)

_Note: TDD plan — two commits (test RED then implementation GREEN)_

## Files Created/Modified
- `agent/models.py` — PropertyListing Pydantic v2 model with is_valid() method
- `agent/url_builder.py` — build_search_url, parse_listings_from_message, PROPERTY_TYPE_MAP
- `tests/test_url_builder.py` — 14 tests for build_search_url and PROPERTY_TYPE_MAP
- `tests/test_parser.py` — 17 tests for parse_listings_from_message and PropertyListing model

## Decisions Made
- Deferred import of BotDetectedError inside parse_listings_from_message function body to avoid ImportError at test collection time when agent/exceptions.py (Plan 02) may not yet exist. This is acceptable and won't change in Phase 4.
- Partial-results contract implemented as instructed by 03-03-PLAN.md: bot_detected=True with non-empty listings returns those listings rather than raising BotDetectedError. Only bot_detected=True with empty listings raises.
- price field type is `str | None` (not float) to preserve display strings like "$450 pw" or "Price on application".

## Deviations from Plan

None - plan executed exactly as written. The exceptions.py file (from Plan 02 running in the same wave) was already present at execution time, confirming the deferred import approach works even if it isn't strictly needed.

## Issues Encountered

None. Both RED (failing) and GREEN (passing) phases completed cleanly. All 39 tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- agent/models.py and agent/url_builder.py are ready for import by agent/property_agent.py (Plan 03)
- parse_listings_from_message honors the partial-results contract expected by Plan 03-03
- All tests documented as living spec for domain.com.au URL format and extraction contract

---
*Phase: 03-langgraph-agent*
*Completed: 2026-02-28*

## Self-Check: PASSED

- agent/models.py: FOUND
- agent/url_builder.py: FOUND
- tests/test_url_builder.py: FOUND
- tests/test_parser.py: FOUND
- 03-01-SUMMARY.md: FOUND
- Commit 7df0bab (RED tests): FOUND
- Commit a089470 (GREEN impl): FOUND
