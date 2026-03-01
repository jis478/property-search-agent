# Phase 5: Frontend - Research

**Researched:** 2026-03-01
**Domain:** Vanilla JS / SSE streaming / Tailwind CSS CDN / single-file HTML UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Styling approach
- Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com"></script>`) — no build step, utility classes, fast to write
- Light theme — white/grey background; property search conventions (Domain, REA) use light themes; listings are easier to scan on white
- Accent color: green (#16a34a / Tailwind green-600) — echoes Domain.com.au brand, works well for price display and CTAs
- Clean, polished aesthetic — looks like a real product, not a dev tool; rounded cards, subtle shadows

#### Search input area
- Single centered text input (full-width, large) with a "Search" button
- Placeholder: "e.g. 2 bedroom apartment in Richmond VIC under $600 per week"
- On submit: disable input + button, show spinner; re-enable on complete/error
- Input clears for a new search only after user explicitly clicks "New search" or the result is shown

#### Interpretation banner
- While searching: show a banner directly below the input — `Searching for: "[original query]"` with a subtle animated pulse/spinner
- Banner stays visible until the `complete` or `error` event arrives
- No attempt to parse/reformat the query — show verbatim; avoids mismatch between what user typed and what we display

#### Live step log
- Displayed below the banner while the agent runs; hidden once complete event arrives (results replace it)
- Each `tool_call` event renders a new log line: icon + plain-English label (from the `label` field already in the SSE event)
  - `browser_navigate` → "🔍 Navigating to [URL]"
  - `browser_take_screenshot` → "📸 Taking screenshot"
  - `browser_wait_for` → "⏳ Waiting for page"
- `tool_result` events: append a brief "✓ Done" or "✗ Failed" tick to the previous tool_call line (don't add a new row)
- `thinking` events: NOT shown token-by-token — accumulate silently; only the tool labels are shown to the user (thinking tokens are too noisy and meaningless to a non-technical user)
- `ping` events: ignored (keep-alive only)
- Step log scrolls as new steps arrive (max height with overflow-y: auto)

#### Listing cards
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

#### Error and empty states
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

### Deferred Ideas (OUT OF SCOPE)
- Saved searches / search history — future phase
- Map view of listings — future phase
- Filter/sort controls on results — future phase
- Mobile responsive polish beyond basic Tailwind breakpoints — could be a follow-up
- Dark mode toggle — future phase if needed
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FRNT-02 | User can submit a natural-language query via web UI | fetch POST /search pattern; disable/enable input state machine |
| FRNT-03 | Frontend streams agent thinking and tool call steps in real-time | EventSource named event types; `tool_call` / `tool_result` DOM update patterns |
| FRNT-04 | Frontend displays structured listing cards after agent completes | `complete` event JSON structure; grid card rendering; nullable field handling |
| FRNT-05 | Interpretation banner shown before results appear | Show/hide div on submit/complete; verbatim query display |
| FRNT-06 | Friendly error messages on failure (bot detection, timeout, zero results) | `error_type` field mapping; `partial` flag; count === 0 detection |
</phase_requirements>

---

## Summary

This phase replaces the stub `templates/index.html` with a fully wired single-page UI. No framework, no build step — pure HTML, Tailwind CSS (via CDN), and vanilla JavaScript. The entire application is one file, served by FastAPI's `Jinja2Templates` at `GET /`.

The critical integration path is: user submits form → `fetch` POST to `/search` → server returns `{run_id}` → open `EventSource('/stream/{run_id}')` → handle typed SSE events (`tool_call`, `tool_result`, `complete`, `error`, `ping`) → update DOM progressively. When a `complete` or `error` event fires, call `eventSource.close()` immediately to prevent the browser's built-in auto-reconnect from firing a second connection.

The entire implementation lives in a single `<script>` block at the bottom of `index.html`. State is managed with plain JS variables (no framework). The UI has four distinct phases: idle → searching (banner + step log) → results (listing grid) → error. A "New Search" button returns to idle and clears previous results.

**Primary recommendation:** Use native `EventSource` for streaming (the stream endpoint is GET, so no workaround is needed), `fetch` for the POST /search initiation, and Tailwind v3 CDN (`cdn.tailwindcss.com`) with an inline `tailwind.config` block to register the custom fade-in animation keyframes.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS CDN | v3 (cdn.tailwindcss.com) | Utility-first CSS, no build step | Locked decision; v3 CDN is the URL already in index.html stub |
| Native `EventSource` | Browser built-in | Consume GET SSE stream | Native API, no CDN needed; stream endpoint is GET |
| Native `fetch` | Browser built-in | POST /search to get run_id | Native API; needed because EventSource cannot POST |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None (vanilla JS) | — | DOM manipulation, state | No framework — single file, no build |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cdn.tailwindcss.com` (v3) | `cdn.jsdelivr.net/npm/@tailwindcss/browser@4` (v4) | v4 CDN is newer but requires `type="text/tailwindcss"` style blocks for config; v3 is already in the stub and uses familiar `tailwind.config` object — stick with what's locked |
| Native `EventSource` | `@microsoft/fetch-event-source` (CDN) | fetch-event-source needed only if stream used POST; since `/stream/{run_id}` is GET, native EventSource is sufficient |
| Inline `<script>` state | Alpine.js via CDN | Alpine adds reactivity at cost of external dep; vanilla JS is simpler for single-file, single-interaction UI |

**Installation:** No npm install. All dependencies are CDN-loaded at runtime.

```html
<!-- Tailwind CSS v3 CDN — in <head> -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Inline Tailwind config — in <head>, AFTER the CDN script -->
<script>
  tailwind.config = {
    theme: {
      extend: {
        animation: {
          'fade-in': 'fadeIn 0.4s ease-out forwards',
        },
        keyframes: {
          fadeIn: {
            '0%': { opacity: '0', transform: 'translateY(8px)' },
            '100%': { opacity: '1', transform: 'translateY(0)' },
          },
        },
      },
    },
  };
</script>
```

---

## Architecture Patterns

### Recommended File Structure

```
templates/
└── index.html        # Single file — all HTML, CSS (Tailwind classes), JS
```

The entire frontend is `templates/index.html`. No separate JS files, no separate CSS files. FastAPI serves it via `Jinja2Templates` at `GET /`. The template uses no Jinja2 variables (the page is static HTML; data arrives over SSE at runtime).

### Pattern 1: UI State Machine (4 Phases)

**What:** The UI transitions through four named states. Each transition shows/hides specific DOM sections.

**When to use:** Always — this is the core page logic.

```
idle → searching → results
                → error
results → idle  (via "New Search" button)
error   → idle  (via "New Search" button)
```

| State | Visible sections | Input state |
|-------|-----------------|-------------|
| idle | search form | enabled |
| searching | search form (disabled) + banner + step log | disabled |
| results | search form + results grid | enabled |
| error | search form + error banner | enabled |

### Pattern 2: Two-Call SSE Integration

**What:** Submit is two steps: `fetch` POST (to get `run_id`), then `new EventSource` (to stream).

**When to use:** Every search submit.

```javascript
// Source: MDN EventSource docs + fetch API docs
async function startSearch(query) {
  // Step 1: POST to get run_id
  const response = await fetch('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) {
    // 409 Conflict = already running; surface friendly error
    const err = await response.json();
    showError(response.status === 409 ? 'conflict' : 'unknown');
    return;
  }
  const { run_id } = await response.json();

  // Step 2: Open SSE stream
  const es = new EventSource(`/stream/${run_id}`);
  es.addEventListener('tool_call', handleToolCall);
  es.addEventListener('tool_result', handleToolResult);
  es.addEventListener('complete', handleComplete);
  es.addEventListener('error', handleSseError);
  // ping: no listener needed — it fires but we ignore it
  // thinking: no listener needed — accumulate silently
  es.onerror = () => { es.close(); showError('connection'); };
}
```

**Critical:** The `complete` and `error` event handlers MUST call `es.close()` immediately. If the connection drops without a `complete`/`error` event, `onerror` fires and the browser would auto-reconnect; calling `es.close()` inside `onerror` prevents the reconnect loop.

### Pattern 3: Named SSE Event Dispatch (addEventListener, not onmessage)

**What:** The server sends typed events (`event: tool_call\ndata: {...}\n\n`). These are NOT received by `onmessage` — they require `addEventListener`.

**When to use:** All custom event types.

```javascript
// Source: MDN - "Using server-sent events"
// onmessage ONLY fires for events with NO event: field
// All our events have event: fields, so addEventListener is required:
es.addEventListener('tool_call', (e) => {
  const data = JSON.parse(e.data);
  appendStepLine(data.tool, data.label);
});

es.addEventListener('tool_result', (e) => {
  const data = JSON.parse(e.data);
  appendTickToPreviousLine(data.success);
});

es.addEventListener('complete', (e) => {
  es.close();          // prevent auto-reconnect
  const data = JSON.parse(e.data);
  renderResults(data);
});

es.addEventListener('error', (e) => {
  es.close();          // prevent auto-reconnect
  const data = JSON.parse(e.data);
  showSseError(data.error_type);
});
```

### Pattern 4: Step Log — Append and Mutate Last Line

**What:** `tool_call` appends a new `<div>` to the log. `tool_result` mutates the last `<div>` by appending a tick. Use a module-level `lastStepEl` variable to track the most recent step line.

**When to use:** During the searching state.

```javascript
let lastStepEl = null;

function appendStepLine(tool, label) {
  const el = document.createElement('div');
  el.className = 'flex items-center gap-2 text-sm font-mono text-gray-700 py-0.5';
  el.textContent = label;
  el.dataset.tool = tool;
  stepLog.appendChild(el);
  stepLog.scrollTop = stepLog.scrollHeight;  // keep newest visible
  lastStepEl = el;
}

function appendTickToPreviousLine(success) {
  if (!lastStepEl) return;
  const tick = document.createElement('span');
  tick.textContent = success ? ' ✓' : ' ✗';
  tick.className = success ? 'text-green-600' : 'text-red-500';
  lastStepEl.appendChild(tick);
}
```

### Pattern 5: Card Rendering with Nullable Field Handling

**What:** Build card HTML from listing object, skipping null fields.

**When to use:** When rendering each listing from `complete.listings[]`.

```javascript
// Source: agent/models.py (PropertyListing model)
// All fields except address and listing_url may be null
function buildCardHTML(listing) {
  const price = listing.price
    ? `<span class="text-green-600 text-lg font-semibold">${listing.price}</span>`
    : `<span class="text-gray-400 text-sm italic">Price on application</span>`;

  const metaParts = [];
  if (listing.bedrooms != null) metaParts.push(`${listing.bedrooms} bed`);
  if (listing.bathrooms != null) metaParts.push(`${listing.bathrooms} bath`);
  if (listing.property_type) metaParts.push(listing.property_type);
  const meta = metaParts.length
    ? `<p class="text-sm text-gray-500">${metaParts.join(' · ')}</p>`
    : '';

  const cta = listing.listing_url
    ? `<a href="${listing.listing_url}" target="_blank" rel="noopener noreferrer"
          class="mt-auto block text-center border border-green-600 text-green-600
                 rounded px-3 py-1.5 text-sm hover:bg-green-50 transition-colors">
          View on Domain →</a>`
    : '';

  return `
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4
                flex flex-col gap-2 animate-fade-in">
      <p class="font-semibold text-gray-900">${listing.address}</p>
      ${price}
      ${meta}
      ${cta}
    </div>`;
}
```

### Pattern 6: Tailwind Custom Animation via Inline Config

**What:** Register `@keyframes` in the `tailwind.config` object so `animate-fade-in` is a valid Tailwind class.

**When to use:** Card grid rendering; cards get the class on creation.

```javascript
// In <head>, after <script src="https://cdn.tailwindcss.com">
tailwind.config = {
  theme: {
    extend: {
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
};
```

Source: Tailwind v3 CDN official docs — `tailwind.config` is set as a global JS object; the Play CDN reads it on load.

### Anti-Patterns to Avoid

- **Using `onmessage` for typed events:** `onmessage` only fires for events with NO `event:` field. Since all server events (`tool_call`, `tool_result`, `complete`, `error`) have an `event:` field, `onmessage` will never fire. Always use `addEventListener`.
- **Not calling `es.close()` on complete/error:** The browser auto-reconnects after ~3 seconds by default. Without explicit `.close()`, the client opens a second stream connection to an already-finished run, receives nothing, and eventually errors.
- **Setting `tailwind.config` after DOMContentLoaded:** The `tailwind.config` object must be set before or immediately after the CDN script loads, not inside a `DOMContentLoaded` callback. The CDN reads it synchronously on initialization.
- **Injecting raw `listing.address` into innerHTML without escaping:** Addresses come from the agent's LLM output. Escape HTML entities before injecting to prevent XSS (even in a local hobby project, this is a safe habit).
- **Polling `run_store` status via HTTP:** The SSE stream IS the status feed. No polling needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE connection management | Custom WebSocket or polling | Native `EventSource` | Handles reconnect logic, event parsing, keep-alive — all automatic |
| Utility CSS | Custom CSS classes | Tailwind CDN classes | Tailwind v3 CDN includes every utility class; no CSS file needed |
| Fade-in animation | Raw CSS `<style>` block | `tailwind.config` keyframes extension | Keeps animation as a Tailwind class (`animate-fade-in`); consistent with the rest of the styling approach |
| JSON parsing of SSE data | Custom SSE text parser | `JSON.parse(event.data)` | The server sends valid JSON in every `data:` field — one-liner parse is sufficient |
| HTTP status detection for 409 | Custom XHR interceptor | `if (!response.ok)` on the `fetch` result | `fetch` exposes `response.status` directly; check before opening EventSource |

**Key insight:** This phase is thin integration glue. The heavy logic lives in the backend. The frontend's only job is: send query, show stream events as DOM updates, render listings array. Resist adding any data transformation or business logic in the browser.

---

## Common Pitfalls

### Pitfall 1: EventSource Auto-Reconnect on Stream End

**What goes wrong:** After the agent finishes and the SSE connection closes server-side, the browser automatically retries the connection every ~3 seconds. The second connection hits `/stream/{run_id}` again; the run_store still exists (TTL is 5 minutes), so it returns 200 with an empty queue. The client hangs indefinitely waiting for events that never come.

**Why it happens:** EventSource is designed for persistent streams (e.g., live feeds). Auto-reconnect is the default behavior. The browser does not distinguish between "server intentionally closed" and "network error."

**How to avoid:** Call `es.close()` inside BOTH the `complete` and `error` event listeners. Also call `es.close()` inside `onerror` to stop the reconnect loop on network failures.

**Warning signs:** Browser DevTools Network tab shows repeated GET requests to `/stream/{run_id}` every few seconds after results appear.

### Pitfall 2: Tailwind `tailwind.config` Timing

**What goes wrong:** Custom animation classes like `animate-fade-in` are not recognized. Cards render without animation.

**Why it happens:** `tailwind.config` was set inside `window.addEventListener('DOMContentLoaded', ...)` or at the bottom of `<body>`. The Tailwind CDN script initializes synchronously as it loads and reads `tailwind.config` at that moment. Setting the config after initialization has no effect.

**How to avoid:** Place the `tailwind.config = {...}` script tag immediately after the `<script src="https://cdn.tailwindcss.com">` tag, both in `<head>`. Do NOT wrap it in any callback.

**Warning signs:** `animate-fade-in` class appears in the DOM but cards have no animation; browser console shows no errors (Tailwind CDN silently ignores unknown animation names).

### Pitfall 3: XSS via `innerHTML` with Unescaped Listing Data

**What goes wrong:** Listing data (address, price, property_type) from the LLM-generated agent output is injected into `innerHTML` directly. A maliciously crafted address like `</p><script>alert(1)</script>` executes arbitrary JS.

**Why it happens:** `innerHTML` processes HTML tags in strings. LLM output is not sanitized.

**How to avoid:** Either use `textContent` for text-only values, or escape HTML entities before string interpolation. A minimal escape function:

```javascript
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
```

Use `esc(listing.address)` in template literals. The `listing_url` (used in `href`) must also be validated to start with `https://` before insertion.

**Warning signs:** Any `<script>` or `<img onerror=...>` pattern in an address field causes unexpected JS execution.

### Pitfall 4: 409 Conflict Not Handled

**What goes wrong:** User submits a search while a previous search is still running. The server returns HTTP 409. The `fetch` response is `!response.ok`. If this is not handled, the code attempts to read `run_id` from a non-JSON error body, throws an exception, and leaves the UI frozen with a disabled input and no feedback.

**Why it happens:** The 409 path is not exercised during happy-path development.

**How to avoid:** Check `response.ok` before `const { run_id } = await response.json()`. On 409, show a user-facing message ("A search is already in progress. Please wait.") and re-enable the form.

**Warning signs:** Submit button stays disabled, page freezes, browser console shows `SyntaxError: Unexpected token` from failed JSON parse.

### Pitfall 5: Step Log Not Scrolled to Bottom

**What goes wrong:** The step log shows the first few lines, but new lines scroll off the bottom of the fixed-height container. The user sees a static old line, not the most recent activity.

**Why it happens:** `overflow-y: auto` containers don't auto-scroll when content is appended programmatically.

**How to avoid:** After every `stepLog.appendChild(el)`, immediately set `stepLog.scrollTop = stepLog.scrollHeight`.

**Warning signs:** Step log appears static even when events are received (visible in Network tab).

### Pitfall 6: `listing_url` Containing `null` in href

**What goes wrong:** `listing.listing_url` is null (agent couldn't extract a URL). If the card template generates `href="null"`, clicking the link navigates to a broken URL.

**Why it happens:** JavaScript string template: `href="${listing.listing_url}"` with `null` becomes the literal string `"null"`.

**How to avoid:** Check `if (listing.listing_url)` before rendering the CTA anchor. The CONTEXT.md decision is to hide the button entirely when URL is missing — so the check is required.

---

## Code Examples

### Full Two-Call SSE Flow

```javascript
// Source: MDN fetch API + MDN EventSource (verified pattern)
let currentEs = null;

async function handleSubmit(event) {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  // Close any previous stream
  if (currentEs) { currentEs.close(); currentEs = null; }

  setUiState('searching', query);

  try {
    // Step 1: POST /search
    const res = await fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      if (res.status === 409) {
        showUiError('A search is already in progress. Please wait.');
      } else {
        showUiError('Something went wrong starting the search.');
      }
      setUiState('idle');
      return;
    }
    const { run_id } = await res.json();

    // Step 2: Open SSE stream
    currentEs = new EventSource(`/stream/${run_id}`);

    currentEs.addEventListener('tool_call', (e) => {
      const d = JSON.parse(e.data);
      appendStepLine(d.tool, d.label);
    });

    currentEs.addEventListener('tool_result', (e) => {
      const d = JSON.parse(e.data);
      appendTickToPreviousLine(d.success);
    });

    currentEs.addEventListener('complete', (e) => {
      currentEs.close(); currentEs = null;
      const d = JSON.parse(e.data);
      setUiState('results', d);
    });

    currentEs.addEventListener('error', (e) => {
      currentEs.close(); currentEs = null;
      const d = JSON.parse(e.data);
      setUiState('error', d.error_type);
    });

    // onerror fires on network failure (not on SSE 'error' event)
    currentEs.onerror = () => {
      currentEs.close(); currentEs = null;
      setUiState('error', 'connection');
    };

  } catch (err) {
    setUiState('error', 'connection');
  }
}
```

### UI State Transitions

```javascript
// Source: application-level pattern from CONTEXT.md decisions
function setUiState(state, data) {
  // Helper: show/hide elements
  // state: 'idle' | 'searching' | 'results' | 'error'
  const isSearching = state === 'searching';
  const isResults   = state === 'results';
  const isError     = state === 'error';

  // Form controls
  queryInput.disabled  = isSearching;
  searchButton.disabled = isSearching;
  spinner.classList.toggle('hidden', !isSearching);

  // Sections
  banner.classList.toggle('hidden',   !isSearching);
  stepLog.classList.toggle('hidden',  !isSearching);
  resultsGrid.classList.toggle('hidden', !isResults);
  errorBanner.classList.toggle('hidden', !isError);

  if (state === 'searching') {
    bannerText.textContent = `Searching for: "${data}"`;
    stepLog.innerHTML = '';
  } else if (state === 'results') {
    renderResults(data);   // data is the complete event payload
  } else if (state === 'error') {
    renderError(data);     // data is error_type string
  }
}
```

### Error Type to Friendly Message Map

```javascript
// Source: CONTEXT.md decisions + api/search.py make_error()
const ERROR_MESSAGES = {
  BotDetectedError: 'Domain.com.au blocked the search. Try again in a moment.',
  StepLimitError:   'The search took too long. Try a more specific query.',
  MCPError:         'Something went wrong. Check the server is running.',
  UnknownError:     'Something went wrong. Check the server is running.',
  connection:       'Lost connection to the server. Please try again.',
  conflict:         'A search is already in progress. Please wait.',
};

function renderError(errorType) {
  errorBanner.textContent = ERROR_MESSAGES[errorType] ?? ERROR_MESSAGES.UnknownError;
}
```

### HTML Escaping Helper

```javascript
// Source: standard XSS prevention pattern
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// URL safety check (only allow https:// links)
function safeUrl(url) {
  if (!url) return null;
  return url.startsWith('https://') ? url : null;
}
```

### Tailwind Custom Animation Registration

```html
<!-- Source: Tailwind v3 CDN official docs (v3.tailwindcss.com/docs/installation/play-cdn) -->
<!-- Must be in <head>, immediately after the CDN script -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        animation: {
          'fade-in': 'fadeIn 0.4s ease-out forwards',
        },
        keyframes: {
          fadeIn: {
            '0%':   { opacity: '0', transform: 'translateY(8px)' },
            '100%': { opacity: '1', transform: 'translateY(0)' },
          },
        },
      },
    },
  };
</script>
```

### Recommended HTML Skeleton

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Property Search</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = { /* animation config above */ };
  </script>
</head>
<body class="bg-gray-50 min-h-screen">

  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-4 py-4">
    <div class="max-w-3xl mx-auto">
      <h1 class="text-xl font-bold text-green-600">Property Search</h1>
    </div>
  </header>

  <main class="max-w-3xl mx-auto px-4 py-8 space-y-6">

    <!-- Search form -->
    <form id="search-form" class="flex gap-2">
      <input id="query-input" type="text"
        placeholder="e.g. 2 bedroom apartment in Richmond VIC under $600 per week"
        class="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-base
               focus:outline-none focus:ring-2 focus:ring-green-500" />
      <button id="search-button" type="submit"
        class="flex items-center gap-2 bg-green-600 text-white rounded-lg
               px-5 py-3 font-medium hover:bg-green-700 disabled:opacity-50">
        <span id="spinner" class="hidden animate-spin">⟳</span>
        Search
      </button>
    </form>

    <!-- Interpretation banner -->
    <div id="banner" class="hidden rounded-lg bg-green-50 border border-green-200
                            px-4 py-3 flex items-center gap-3 animate-pulse">
      <span class="text-green-700 text-sm" id="banner-text"></span>
    </div>

    <!-- Live step log -->
    <div id="step-log" class="hidden bg-white rounded-lg border border-gray-100
                              px-4 py-3 max-h-64 overflow-y-auto space-y-0.5 font-mono text-sm">
    </div>

    <!-- Error banner -->
    <div id="error-banner" class="hidden rounded-lg bg-red-50 border border-red-200
                                  px-4 py-3 text-red-700 text-sm"></div>

    <!-- Results grid (max-w expanded for grid) -->
  </main>

  <!-- Results grid — outside max-w-3xl to allow full-width on large screens -->
  <section id="results-grid" class="hidden max-w-7xl mx-auto px-4 pb-12">
    <div id="results-warning" class="hidden mb-4 rounded-lg bg-amber-50 border
                                     border-amber-200 px-4 py-3 text-amber-700 text-sm"></div>
    <div id="card-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
    <div id="no-results" class="hidden text-center text-gray-500 py-12 text-base">
      No listings found. Try broadening your search.
    </div>
  </section>

  <script>
    /* All JS here */
  </script>
</body>
</html>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `cdn.tailwindcss.com` (v3 CDN) | `cdn.jsdelivr.net/npm/@tailwindcss/browser@4` (v4 CDN) | Tailwind v4 GA, Jan 2025 | v4 CDN uses different script URL and config syntax (`@theme` in `<style>` block instead of `tailwind.config` JS object). v3 CDN still works and is the locked decision. |
| Tailwind v3 `tailwind.config` JS object | Tailwind v4 `@theme {}` CSS block in `<style type="text/tailwindcss">` | Tailwind v4, 2025 | Different customization model — irrelevant since v3 CDN is locked |
| `xhr` / `XMLHttpRequest` for POST | `fetch()` | ~2018, now universal | `fetch` is the modern standard; no XHR needed |

**Deprecated/outdated:**
- `evtSource.onmessage` for typed events: Works only for events with no `event:` field. All events in this system have `event:` fields; use `addEventListener` exclusively.
- `XMLHttpRequest` for POST /search: `fetch` is the modern standard in all targeted browsers.

---

## Open Questions

1. **Jinja2 template variables needed?**
   - What we know: `main.py` calls `templates.TemplateResponse(request, "index.html")` with no extra context dict — the template receives only `request`.
   - What's unclear: Is there any runtime config the template should receive (e.g., API base URL)? Since the app is always self-hosted and the frontend calls `/search` and `/stream/{run_id}` (same-origin relative URLs), no Jinja2 variables are needed.
   - Recommendation: Keep template static (no `{{ }}` expressions). Use relative paths (`/search`, `/stream/`) — no base URL injection needed.

2. **Search concurrency UX when 409 fires**
   - What we know: POST /search returns 409 if `_current_run_id is not None`. There is no "wait for completion" endpoint — the UI must check again.
   - What's unclear: Should the UI automatically retry after a delay, or just show an error?
   - Recommendation: Show the friendly "A search is already in progress. Please wait." message and re-enable the form immediately. Don't auto-retry. Retrying creates complexity with no clear benefit for a single-user hobby project.

3. **`listing_url` domain — always Domain.com.au?**
   - What we know: The agent scrapes Domain.com.au. `listing_url` is nullable and the model validation (in `agent/models.py`) only checks `bool(listing_url)`.
   - What's unclear: Can `listing_url` be a non-https URL?
   - Recommendation: Use a `safeUrl()` check that only passes through URLs starting with `https://` — defensive coding, prevents open redirect if LLM hallucinates a URL.

---

## Sources

### Primary (HIGH confidence)
- `v3.tailwindcss.com/docs/installation/play-cdn` — CDN script tag, `tailwind.config` customization pattern, animation extension
- `developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events` — EventSource API, named events require `addEventListener`, `.close()` behavior
- `javascript.info/server-sent-events` — auto-reconnect behavior, `eventSource.close()` prevents reconnect, typed event dispatch
- `/home/mark/hobby/api/search.py` — exact SSE event shapes (`make_tool_call`, `make_tool_result`, `make_complete`, `make_error`)
- `/home/mark/hobby/api/stream.py` — SSE generator, ping behavior, sentinel handling
- `/home/mark/hobby/agent/models.py` — `PropertyListing` field nullability contract
- `/home/mark/hobby/agent/exceptions.py` — error type names (`BotDetectedError`, `StepLimitError`, `MCPError`)
- `/home/mark/hobby/main.py` — template serving pattern (`Jinja2Templates`, `GET /` route)

### Secondary (MEDIUM confidence)
- `tailkits.com/blog/tailwind-css-v4-cdn-setup/` — confirms v3 vs v4 CDN URL difference (verified against official docs)
- `github.com/tailwindlabs/tailwindcss/discussions/7637` — community confirmation that cdn.tailwindcss.com is v3 Play CDN, development-only

### Tertiary (LOW confidence)
- None — all findings verified with official sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Tailwind v3 CDN and native EventSource both verified against official docs; no npm required
- Architecture: HIGH — SSE event shapes and field nullability derived directly from production server code
- Pitfalls: HIGH (auto-reconnect, config timing) / MEDIUM (XSS) — reconnect and config timing verified against MDN and official Tailwind docs; XSS is standard web security practice

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (Tailwind CDN URLs are stable; EventSource API is a living standard with no breaking changes expected)
