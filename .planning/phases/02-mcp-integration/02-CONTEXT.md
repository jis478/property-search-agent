# Phase 2: MCP Integration - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate the `@playwright/mcp` Node.js subprocess into the FastAPI process lifecycle — spawns at server startup, exposes browser tools to the LangGraph agent, shuts down cleanly. No user-visible UI changes. This phase produces managed subprocess infrastructure; the agent that calls those tools is Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Startup failure behavior
- **Hard fail** — if the MCP subprocess fails to start, FastAPI must refuse to start entirely
- No degraded mode: the server has no value without browser tools
- **One-line error** in server log: e.g. `ERROR: MCP subprocess failed — check Node.js and @playwright/mcp installation`
- **5-second timeout** — if MCP isn't ready within 5 seconds, treat as failure
- **No retry** — fail immediately on first error; deterministic, no ambiguous half-started state

### Crash recovery
- A "crash" is: subprocess exits unexpectedly, stdio pipe breaks, or a request to MCP times out (10s threshold)
- **Current request fails** with a clear error returned to the caller (no silent retry of the failed request)
- **Auto-restart** the subprocess for future requests — up to 3 restart attempts before giving up
- If MCP is down (crashed, restart attempts exhausted): `GET /health` returns `{"status": "degraded", "mcp": "down"}`
- Normal operation: `GET /health` returns `{"status": "ok", "mcp": "ready"}`

### Tool discoverability
- **Both** startup log and endpoint:
  - Startup log: `INFO: MCP ready — {N} tools available` (list tool names at DEBUG level)
  - `GET /tools` endpoint returns the full tool list as JSON — useful for testing and Phase 3 agent setup verification
- This satisfies the ROADMAP success criterion: "enumerable from a test endpoint or startup log"

### Dev/reload behavior
- MCP subprocess is **fully managed by the FastAPI lifespan context manager**
- `uvicorn --reload` triggers lifespan shutdown (kill MCP subprocess + Chromium) then lifespan startup (spawn fresh MCP)
- This is **automatic** — no manual intervention needed for normal file-change reloads
- Note: first startup may download Chromium (~100MB via `npx playwright install chromium`); subsequent restarts are fast (~1-2s)
- If MCP configuration changes (e.g. browser type flag), a manual server restart is still required (config read from env at startup)

### Claude's Discretion
- Exact stdio protocol / handshake implementation (use `langchain-mcp-adapters` `MultiServerMCPClient` as researched)
- How to store the MCP client reference in `app.state` (e.g. `app.state.mcp_client`)
- Exact subprocess command construction (e.g. `npx @playwright/mcp --browser chromium`)
- Chromium installation check at startup vs at first use
- Restart backoff strategy (immediate vs exponential)

</decisions>

<specifics>
## Specific Ideas

- The `langchain-mcp-adapters` `MultiServerMCPClient` should be the bridge — already researched as the standard approach
- Chromium browser mode (not Firefox or WebKit) for domain.com.au compatibility
- The `mcp/` package stub created in Phase 1 is where subprocess management code lives

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-mcp-integration*
*Context gathered: 2026-02-20*
