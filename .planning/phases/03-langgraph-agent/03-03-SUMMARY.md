---
phase: 03-langgraph-agent
plan: 03
subsystem: agent
tags: [langgraph, langchain-openai, create_react_agent, property-agent, tool-filtering]

# Dependency graph
requires:
  - phase: 03-01
    provides: parse_listings_from_message, PropertyListing, build_search_url
  - phase: 03-02
    provides: agent/exceptions.py (StepLimitError, BotDetectedError), agent/prompts.py (SYSTEM_PROMPT), langgraph 1.0.10 + langchain-openai 1.1.10
provides:
  - build_agent: constructs LangGraph ReAct agent with GPT-4o, 3-tool filter, SYSTEM_PROMPT
  - search_properties: async ainvoke wrapper with recursion_limit=15, StepLimitError translation, partial-results contract
  - agent package public API (__all__) for flat Phase 4 imports
affects:
  - 04-sse (Phase 4 imports build_agent, search_properties, PropertyListing, BotDetectedError from agent package root)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Tool filtering at build_agent — REQUIRED_TOOLS set guards against step budget waste
    - recursion_limit=15 passed via config dict at ainvoke time (RunnableConfig field, not create_react_agent param)
    - Deferred imports in search_properties body for GraphRecursionError and StepLimitError
    - Partial-results contract fully delegated to parse_listings_from_message

key-files:
  created:
    - agent/property_agent.py
  modified:
    - agent/__init__.py

key-decisions:
  - "recursion_limit=15 passed via config={'recursion_limit': 15} at ainvoke time — create_react_agent in langgraph 1.0.10 does not accept recursion_limit as a constructor param; it is a RunnableConfig field"
  - "Tool filtering at build_agent: REQUIRED_TOOLS = {browser_navigate, browser_take_screenshot, browser_wait_for} — only 3 of ~22 Playwright MCP tools admitted to agent"
  - "Partial-results contract fully delegated to parse_listings_from_message — no inline JSON parsing in search_properties"

patterns-established:
  - "search_properties: GraphRecursionError -> StepLimitError translation at agent boundary"
  - "build_agent returns unbound graph; recursion_limit is enforced at invocation time"
  - "agent/__init__.py as flat import surface for Phase 4 — no deep submodule imports needed"

requirements-completed: [AGNT-01, AGNT-02, AGNT-03, AGNT-04, SCRP-02, SCRP-03, SCRP-04, SCRP-05]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 3 Plan 03: LangGraph Agent Wiring Summary

**LangGraph ReAct agent with GPT-4o, 3-tool filter, recursion_limit=15 via RunnableConfig, and StepLimitError/BotDetectedError translation — wired to parse_listings_from_message for the partial-results contract**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-28T03:34:09Z
- **Completed:** 2026-02-28T03:35:48Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `agent/property_agent.py` with:
  - `build_agent(mcp_tools)` — filters to REQUIRED_TOOLS, builds ChatOpenAI(gpt-4o) + create_react_agent with SYSTEM_PROMPT
  - `search_properties(agent, query)` — async ainvoke with recursion_limit=15, GraphRecursionError -> StepLimitError translation, delegates all JSON parsing and bot detection to parse_listings_from_message
- Updated `agent/__init__.py` with full public API (7 symbols in __all__) for flat Phase 4 imports
- Full import chain verified; all 8 existing tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: property_agent.py** - `07a8ee5` (feat)
2. **Task 2: agent/__init__.py public API** - `addfcce` (feat)

## Files Created/Modified

- `agent/property_agent.py` — build_agent + search_properties with error contract
- `agent/__init__.py` — public API: build_agent, search_properties, PropertyListing, PropertyAgentError, BotDetectedError, StepLimitError, MCPError

## Decisions Made

- `recursion_limit=15` is passed via `config={"recursion_limit": _RECURSION_LIMIT}` at `ainvoke` time, not as a `create_react_agent` constructor argument. In langgraph 1.0.10 `create_react_agent` does not accept `recursion_limit` as a keyword argument; it is a field on `RunnableConfig` passed at invocation. The plan's pseudocode showed it at construction time, but the correct implementation enforces it at invocation — same effective behavior.
- Tool filtering is done inside `build_agent` using a `REQUIRED_TOOLS` set, admitting only the 3 browser tools needed for domain.com.au scraping out of the ~22 Playwright MCP tools.
- All JSON parsing, bot detection, and the partial-results contract are delegated entirely to `parse_listings_from_message` — no inline logic in `search_properties`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] recursion_limit passed at ainvoke time, not create_react_agent constructor**
- **Found during:** Task 1 verification
- **Issue:** Plan pseudocode showed `create_react_agent(..., recursion_limit=15)` but langgraph 1.0.10 raises `TypeError: create_react_agent() got unexpected keyword arguments: {'recursion_limit': 15}`. The `recursion_limit` field belongs to `RunnableConfig`, not the graph constructor.
- **Fix:** Pass `config={"recursion_limit": 15}` in `agent.ainvoke(...)` inside `search_properties`. Effective behavior is identical — limit is enforced on every invocation.
- **Files modified:** `agent/property_agent.py`
- **Commit:** `07a8ee5`

## Issues Encountered

None beyond the auto-fixed deviation above. Import chain verified clean; all tests pass.

## User Setup Required

None — agent construction works without OPENAI_API_KEY at import time (key only needed at invocation time when ainvoke is called).

## Next Phase Readiness

- Phase 4 SSE endpoints can import `from agent import build_agent, search_properties, PropertyListing, BotDetectedError` — flat imports, no deep submodule paths
- `build_agent(mcp_tools)` is ready to receive tools from `app.state.mcp_tools` (Phase 2 lifespan)
- `search_properties` handles all three error cases: normal list, partial list (partial bot mid-run), StepLimitError, BotDetectedError — Phase 4 can type-switch cleanly

---
*Phase: 03-langgraph-agent*
*Completed: 2026-02-28*

## Self-Check: PASSED

- agent/property_agent.py: FOUND
- agent/__init__.py: FOUND (updated)
- 03-03-SUMMARY.md: FOUND
- Commit 07a8ee5 (Task 1): FOUND
- Commit addfcce (Task 2): FOUND
