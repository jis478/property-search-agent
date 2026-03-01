---
plan: 05-02
phase: 05-frontend
type: summary
status: complete
completed: 2026-03-01
---

# Summary: 05-02 Card Grid, Error States, Human Verification

## One-liner
Complete listing card grid with all nullable-field guards and error states implemented; human verification passed via console injection.

## What Was Built
Replaced the `renderResults` stub from Plan 01 with full implementation:

- **`buildCardHTML(listing)`**: 1/2/3 column Tailwind grid, `animate-fade-in` on cards, green price or "Price on application" fallback, beds·baths·type meta row, `safeUrl()`-guarded "View on Domain →" button
- **Null guards**: `bedrooms != null` (not `!bedrooms` — 0 is valid), `property_type` falsy check, `safeUrl()` prevents `href="null"`
- **Empty state**: "No listings found. Try broadening your search." when count=0
- **Partial results**: Amber warning banner when `partial: true`
- **Error states**: All 4 error types → friendly messages (BotDetectedError, StepLimitError, MCPError, UnknownError)

## Bug Fixes During Execution

### `onerror` double-fire (frontend)
`showError(ERROR_MESSAGES.connection)` was outside the `if (currentEs)` guard in `onerror`, causing "Lost connection" to always fire after `complete` or `error` closed the stream. Fixed by moving it inside the guard, and adding `if (!currentEs) return` to `addEventListener('error', ...)`.

### `_final_text` accumulation (backend)
`run_agent` was concatenating all LLM streaming chunks across all LLM calls (`+=`), polluting `_final_text` with intermediate reasoning text. Fixed by switching to `on_chat_model_end` which captures the last complete LLM response (overwrite, not append) — matching how `search_properties` works.

### Plain-English fallback (backend)
When the agent outputs plain English error text instead of JSON (domain.com.au bot detection not triggering the JSON path), `parse_listings_from_message` returned `[]` and showed "No listings found". Fixed by detecting the no-`"listings"`-key case and raising `BotDetectedError` → friendly error message instead.

### System prompt (agent)
- Pagination: "replace page=1 with page=2" instead of the ambiguous "append ?page=2" which caused double-`?` URLs
- Broader bot detection: catches any page with no visible listing cards, not just CAPTCHA text
- Hard mandate: "CRITICAL: Your final message MUST be a single JSON object"

## Human Verification
Verified via browser console injection (domain.com.au blocks headless Playwright):
- Normal card: address, green price, beds/baths/type, View on Domain button ✓
- Null-field card: "Price on application", no meta row, no button ✓
- Card grid renders in 1/2/3 columns ✓
- `animate-fade-in` visible on card appearance ✓
- Frontend correctly shows "Domain.com.au blocked the search. Try again in a moment." for bot detection ✓

## Key Files Modified
- `templates/index.html` — complete frontend (293 lines)
- `api/search.py` — `on_chat_model_end` fix, plain-English fallback detection
- `agent/prompts.py` — pagination fix, broader bot detection, JSON mandate

## All Tests
46/46 passing
