---
phase: 03-langgraph-agent
plan: 02
subsystem: agent
tags: [langgraph, langchain-openai, exceptions, prompts, python]

# Dependency graph
requires:
  - phase: 02-mcp-integration
    provides: langchain-mcp-adapters installed, MCP tools available via app.state.mcp_tools
provides:
  - Exception hierarchy for all agent failure modes (PropertyAgentError, BotDetectedError, StepLimitError, MCPError)
  - SYSTEM_PROMPT for LangGraph ReAct agent with tool restriction and JSON output format
  - langgraph 1.0.10 and langchain-openai 1.1.10 installed in conda env
affects:
  - 03-03 (property_agent.py imports from agent.exceptions and agent.prompts)
  - 04-sse (SSE error events type-switch on BotDetectedError, StepLimitError, MCPError)

# Tech tracking
tech-stack:
  added:
    - langgraph==1.0.10 (create_react_agent, GraphRecursionError)
    - langgraph-prebuilt==1.0.8
    - langgraph-checkpoint==4.0.1
    - langchain-openai==1.1.10 (ChatOpenAI)
    - tiktoken==0.12.0 (OpenAI tokenizer, transitive)
    - openai==2.24.0 (upgraded from 2.17.0)
  patterns:
    - Exception hierarchy with typed failure modes for Phase 4 SSE type-switching
    - Directive system prompt with explicit tool allowlist and JSON output schema
    - 3-page scrape loop: navigate -> wait 2s -> screenshot, for page=1/2/3

key-files:
  created:
    - agent/exceptions.py
    - agent/prompts.py
  modified:
    - requirements.txt

key-decisions:
  - "langgraph 1.0.10 installed (>=1.0.9 constraint satisfied; latest patch)"
  - "openai upgraded 2.17.0 -> 2.24.0 as transitive dep of langchain-openai (no breaking changes)"
  - "SYSTEM_PROMPT explicitly restricts to 3 tools only: browser_navigate, browser_take_screenshot, browser_wait_for"
  - "bot_detected flag in JSON output format (not an exception at prompt level — parsing raises BotDetectedError)"

patterns-established:
  - "Pattern: Exception hierarchy — all agent errors inherit from PropertyAgentError for catch-all handling"
  - "Pattern: Directive system prompt — explicit tool allowlist prevents agent from using all 22 Playwright tools"
  - "Pattern: JSON output format with bot_detected flag enables parser to raise typed exceptions"

requirements-completed: [AGNT-01, AGNT-04, SCRP-04]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 3 Plan 02: Exceptions, Prompts, and Dependencies Summary

**PropertyAgentError hierarchy with 3 typed failure modes, LangGraph ReAct system prompt with explicit tool restriction and JSON output format, and langgraph 1.0.10 + langchain-openai 1.1.10 installed**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T03:27:04Z
- **Completed:** 2026-02-28T03:29:14Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `agent/exceptions.py` with typed exception hierarchy (PropertyAgentError base + BotDetectedError, StepLimitError, MCPError)
- Created `agent/prompts.py` with SYSTEM_PROMPT covering all 7 constraints: tool restriction, 3-page iteration, JSON output format, all 6 listing fields, bot detection visual cues, minimum viable listing, and step budget hint
- Installed langgraph 1.0.10 and langchain-openai 1.1.10 into rental-search conda env; all imports verified

## Task Commits

Each task was committed atomically:

1. **Task 1: Exception classes** - `e7e41bb` (feat)
2. **Task 2: System prompt** - `8c3b75c` (feat)
3. **Task 3: Install langgraph and langchain-openai** - `acfe8e7` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `agent/exceptions.py` - PropertyAgentError base + BotDetectedError, StepLimitError, MCPError typed exceptions
- `agent/prompts.py` - SYSTEM_PROMPT for LangGraph ReAct agent
- `requirements.txt` - Added langgraph>=1.0.9,<2 and langchain-openai>=1.1.10,<2

## Decisions Made

- langgraph 1.0.10 was installed (>=1.0.9 constraint satisfied; latest patch release, no issues)
- openai upgraded from 2.17.0 to 2.24.0 as a transitive dependency of langchain-openai — pip handled this automatically, no breaking changes expected
- SYSTEM_PROMPT explicitly allows only 3 tools (browser_navigate, browser_take_screenshot, browser_wait_for) and explicitly prohibits others (browser_click, browser_fill_form, etc.) — prevents step budget waste
- bot_detected flag is in the JSON output format; the parser (Plan 03-01) will raise BotDetectedError upon seeing bot_detected=true — clean separation between prompt-level signaling and Python exception raising

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all verifications passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `agent/exceptions.py` is ready for import by Plan 03-01 (url_builder.py raises BotDetectedError) and Plan 03-03 (property_agent.py)
- `agent/prompts.py` is ready for import by Plan 03-03 (create_react_agent receives SYSTEM_PROMPT)
- langgraph and langchain-openai are installed; Plan 03-03 can proceed with create_react_agent and ChatOpenAI
- Phase 4 SSE can type-switch on BotDetectedError, StepLimitError, MCPError to emit typed error events

---
*Phase: 03-langgraph-agent*
*Completed: 2026-02-28*

## Self-Check: PASSED

- agent/exceptions.py: FOUND
- agent/prompts.py: FOUND
- requirements.txt: FOUND
- 03-02-SUMMARY.md: FOUND
- Commit e7e41bb (Task 1): FOUND
- Commit 8c3b75c (Task 2): FOUND
- Commit acfe8e7 (Task 3): FOUND
