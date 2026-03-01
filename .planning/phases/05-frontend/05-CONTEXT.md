# Phase 5: Frontend - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the existing single HTML file (`templates/index.html`) to the SSE API. User types a natural-language query, watches live agent activity, and sees structured listing cards on completion. No build step — single HTML file served by FastAPI Jinja2Templates. All decisions below were made by Claude on user's behalf.

</domain>

<decisions>
## Implementation Decisions

### Styling approach
- Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com"></script>`) — no build step, utility classes, fast to write
- Light theme — white/grey background; property search conventions (Domain, REA) use light themes; listings are easier to scan on white
- Accent color: green (#16a34a / Tailwind green-600) — echoes Domain.com.au brand, works well for price display and CTAs
- Clean, polished aesthetic — looks like a real product, not a dev tool; rounded cards, subtle shadows

### Search input area
- Single centered text input (full-width, large) with a "Search" button
- Placeholder: "e.g. 2 bedroom apartment in Richmond VIC under $600 per week"
- On submit: disable input + button, show spinner; re-enable on complete/error
- Input clears for a new search only after user explicitly clicks "New search" or the result is shown

### Interpretation banner
- While searching: show a banner directly below the input — `Searching for: "[original query]"` with a subtle animated pulse/spinner
- Banner stays visible until the `complete` or `error` event arrives
- No attempt to parse/reformat the query — show verbatim; avoids mismatch between what user typed and what we display

### Live step log
- Displayed below the banner while the agent runs; hidden once complete event arrives (results replace it)
- Each `tool_call` event renders a new log line: icon + plain-English label (from the `label` field already in the SSE event)
  - `browser_navigate` → "🔍 Navigating to [URL]"
  - `browser_take_screenshot` → "📸 Taking screenshot"
  - `browser_wait_for` → "⏳ Waiting for page"
- `tool_result` events: append a brief "✓ Done" or "✗ Failed" tick to the previous tool_call line (don't add a new row)
- `thinking` events: NOT shown token-by-token — accumulate silently; only the tool labels are shown to the user (thinking tokens are too noisy and meaningless to a non-technical user)
- `ping` events: ignored (keep-alive only)
- Step log scrolls as new steps arrive (max height with overflow-y: auto)

### Listing cards
- Grid layout: 1 column on mobile, 2 on tablet (md:), 3 on wide desktop (xl:)
- Each card shows:
  - **Address** — bold, prominent (top)
  - **Price** — green, large — the most important field for renters
  - **Beds · Baths · Type** — single muted row below price
  - **"View on Domain →"** link — full-width button at card bottom, opens in new tab
- Missing price: show "Price on application" in muted grey
- Missing URL: hide the "View on Domain" button entirely (don't show a broken link)
- Missing beds/baths: omit that field from the row (don't show "null")
- Cards appear with a subtle fade-in animation as the grid renders

### Error and empty states
- `error` event (bot detection, step limit, MCP failure): show a red/amber banner with a friendly message
  - BotDetectedError → "Domain.com.au blocked the search. Try again in a moment."
  - StepLimitError → "The search took too long. Try a more specific query."
  - MCPError / UnknownError → "Something went wrong. Check the server is running."
- Zero listings (complete with count: 0): show a neutral message — "No listings found. Try broadening your search."
- Partial results (partial: true flag on complete event): show listings + a warning banner — "Some results may be incomplete — Domain.com.au may have partially blocked the search."
- No loading skeleton — step log gives the user enough live feedback; a skeleton would be redundant

### Claude's Discretion
- Exact Tailwind class choices, spacing, and typography scale
- Exact CSS animation for card fade-in
- Whether to use a `<dialog>` or inline div for error messages
- Mobile breakpoint handling details
- Whether to show a "copy query" or "share" button (lean toward no — out of scope)

</decisions>

<specifics>
## Specific Ideas

- Domain.com.au visual reference — green accent, white cards, clean sans-serif; our UI should feel adjacent to that aesthetic without copying it
- Step log should feel like a terminal or a "processing" log, not a chat thread — left-aligned, monospace-adjacent font for the log lines is fine
- The "View on Domain →" CTA should be visually distinct — a green outlined button or text link with arrow, not a heavy filled button (the card itself is already prominent)

</specifics>

<deferred>
## Deferred Ideas

- Saved searches / search history — future phase
- Map view of listings — future phase
- Filter/sort controls on results — future phase
- Mobile responsive polish beyond basic Tailwind breakpoints — could be a follow-up
- Dark mode toggle — future phase if needed

</deferred>

---

*Phase: 05-frontend*
*Context gathered: 2026-03-01*
