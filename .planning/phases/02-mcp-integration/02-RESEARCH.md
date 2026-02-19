# Phase 2: MCP Integration - Research

**Researched:** 2026-02-20
**Domain:** MCP subprocess lifecycle management, langchain-mcp-adapters, @playwright/mcp, FastAPI lifespan
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Startup failure behavior**
- Hard fail — if the MCP subprocess fails to start, FastAPI must refuse to start entirely
- No degraded mode: the server has no value without browser tools
- One-line error in server log: e.g. `ERROR: MCP subprocess failed — check Node.js and @playwright/mcp installation`
- 5-second timeout — if MCP isn't ready within 5 seconds, treat as failure
- No retry — fail immediately on first error; deterministic, no ambiguous half-started state

**Crash recovery**
- A "crash" is: subprocess exits unexpectedly, stdio pipe breaks, or a request to MCP times out (10s threshold)
- Current request fails with a clear error returned to the caller (no silent retry of the failed request)
- Auto-restart the subprocess for future requests — up to 3 restart attempts before giving up
- If MCP is down (crashed, restart attempts exhausted): `GET /health` returns `{"status": "degraded", "mcp": "down"}`
- Normal operation: `GET /health` returns `{"status": "ok", "mcp": "ready"}`

**Tool discoverability**
- Both startup log and endpoint:
  - Startup log: `INFO: MCP ready — {N} tools available` (list tool names at DEBUG level)
  - `GET /tools` endpoint returns the full tool list as JSON — useful for testing and Phase 3 agent setup verification
- This satisfies the ROADMAP success criterion: "enumerable from a test endpoint or startup log"

**Dev/reload behavior**
- MCP subprocess is fully managed by the FastAPI lifespan context manager
- `uvicorn --reload` triggers lifespan shutdown (kill MCP subprocess + Chromium) then lifespan startup (spawn fresh MCP)
- This is automatic — no manual intervention needed for normal file-change reloads
- Note: first startup may download Chromium (~100MB via `npx playwright install chromium`); subsequent restarts are fast (~1-2s)
- If MCP configuration changes (e.g. browser type flag), a manual server restart is still required (config read from env at startup)

### Claude's Discretion
- Exact stdio protocol / handshake implementation (use `langchain-mcp-adapters` `MultiServerMCPClient` as researched)
- How to store the MCP client reference in `app.state` (e.g. `app.state.mcp_client`)
- Exact subprocess command construction (e.g. `npx @playwright/mcp --browser chromium`)
- Chromium installation check at startup vs at first use
- Restart backoff strategy (immediate vs exponential)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCRP-01 | Playwright MCP server (`@playwright/mcp`) spawns as a subprocess at FastAPI startup and is cleanly shut down at FastAPI shutdown | FastAPI lifespan pattern (asynccontextmanager), asyncio subprocess API, `MultiServerMCPClient` persistent session pattern, SIGTERM/SIGKILL cleanup sequence, `start_new_session=True` + `os.killpg` for child process group termination |
</phase_requirements>

---

## Summary

Phase 2 wires `@playwright/mcp` (Node.js, version 0.0.68) into the FastAPI process lifecycle using `langchain-mcp-adapters` (Python, version 0.2.1) as the bridge. The architecture is: FastAPI lifespan starts a persistent MCP `ClientSession` (not ephemeral), which spawns the Node.js subprocess once and keeps it alive for the server's lifetime. All Playwright browser tools are loaded once at startup, stored in `app.state`, and served from `GET /tools`. On shutdown, the MCP session closes cleanly, then the subprocess receives SIGTERM followed by SIGKILL if needed.

The critical non-obvious finding is about `MultiServerMCPClient.get_tools()`: it spawns a fresh subprocess per call (ephemeral by design). For a long-running FastAPI server, the correct pattern is `client.session("playwright")` as an `asynccontextmanager` kept alive in lifespan — not repeated `get_tools()` calls. Tools are loaded once into `app.state.mcp_tools` at startup and reused for the server's lifetime.

The environment is WSL2 Linux (confirmed: kernel `6.6.87.2-microsoft-standard-WSL2`). Chromium requires `--no-sandbox` in WSL2. The `@playwright/mcp` CLI flag for this is `--no-sandbox` (verified in v0.0.68; an earlier rename to `--no-chromium-sandbox` was reverted in v0.0.68). The default browser when no `--browser` flag is given is the open-source Chromium downloaded by `npx playwright install chromium`. Do not use `--browser chrome` (requires Google Chrome installed); omit `--browser` entirely to use the downloaded Chromium.

**Primary recommendation:** Use `MultiServerMCPClient` with a persistent `session()` context manager in the FastAPI lifespan. Spawn the subprocess with `npx @playwright/mcp --headless --no-sandbox --isolated`. Store the loaded tools in `app.state.mcp_tools`. Use `start_new_session=True` in the subprocess and `os.killpg` on shutdown to ensure all Chromium child processes are killed.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-mcp-adapters` | `>=0.2.1,<0.3` | Python bridge from MCP stdio to LangChain tools | Official LangChain package; wraps MCP protocol, converts tools to `BaseTool`; already decided |
| `mcp` | `>=1.9.2` (transitive) | MCP protocol SDK; pulled in by langchain-mcp-adapters | Anthropic's official MCP SDK |
| `@playwright/mcp` | `0.0.68` (npm) | Node.js MCP server providing browser automation tools | Microsoft's official Playwright MCP server |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `asyncio` (stdlib) | Subprocess creation and management | Already in stdlib; `asyncio.create_subprocess_exec` for the subprocess |
| `signal` (stdlib) | SIGTERM/SIGKILL for subprocess cleanup | Process group termination with `os.killpg` |
| `os` (stdlib) | `os.killpg` for process group termination | Kills Chromium children when MCP subprocess is terminated |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langchain-mcp-adapters` | Raw `mcp` SDK + manual JSON-RPC | Much more boilerplate; `langchain-mcp-adapters` handles handshake, tool conversion, session lifecycle |
| persistent `session()` | `get_tools()` per request | `get_tools()` spawns a fresh subprocess each call — unacceptable for a long-running server |
| `npx @playwright/mcp` | `node /path/to/index.js` | npx works without global install; requires Node.js 18+ (confirmed available: v18.20.8) |

### Installation
```bash
# Python (add to requirements.txt)
pip install langchain-mcp-adapters>=0.2.1

# Node.js subprocess (no install needed — npx handles it)
npx playwright install chromium   # First-time setup: downloads ~100MB Chromium binary
```

**requirements.txt additions:**
```
langchain-mcp-adapters>=0.2.1,<0.3
```

**Node.js prerequisite:** Node.js 18+ required. Confirmed available at `/home/mark/.nvm/versions/node/v18.20.8/bin/node` (v18.20.8).

---

## Architecture Patterns

### Recommended Project Structure
```
mcp/
├── __init__.py          # Package; exports MCPManager
└── manager.py           # MCPManager class: spawn, health-check, restart, shutdown logic
main.py                  # lifespan calls mcp/manager.py; adds GET /health and GET /tools
```

All MCP subprocess logic belongs in `mcp/manager.py`, not inlined into `main.py`. The lifespan in `main.py` calls the manager; routes call `request.app.state`.

### Pattern 1: Persistent MCP Session in FastAPI Lifespan

**What:** Open a single `ClientSession` at startup, keep it alive for the server's lifetime, close it on shutdown. Store the loaded tools list in `app.state`.

**When to use:** Always — for a long-running FastAPI server. `get_tools()` spawns a subprocess per call; `session()` reuses the same one.

**Critical detail:** `MultiServerMCPClient` is NOT an async context manager as of v0.1.0+ (raises `NotImplementedError` on `__aenter__`). Use `client.session("playwright")` instead.

```python
# Source: langchain-mcp-adapters v0.2.1 API (verified from GitHub source + DeepWiki)
# mcp/manager.py

import asyncio
import logging
import os
import signal
from contextlib import asynccontextmanager
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

MCP_STARTUP_TIMEOUT = 5.0    # seconds — hard fail if not ready
MCP_REQUEST_TIMEOUT = 10.0   # seconds — crash threshold per CONTEXT.md
MAX_RESTART_ATTEMPTS = 3


class MCPManager:
    """Manages the @playwright/mcp subprocess lifecycle."""

    def __init__(self):
        self._client: MultiServerMCPClient | None = None
        self._session_cm = None        # the async context manager from client.session()
        self._session = None           # the active ClientSession
        self._tools: list[Any] = []
        self._restart_count: int = 0
        self._ready: bool = False

    def _make_client(self) -> MultiServerMCPClient:
        return MultiServerMCPClient(
            connections={
                "playwright": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": [
                        "@playwright/mcp",
                        "--headless",
                        "--no-sandbox",   # Required for WSL2 / Linux containers
                        "--isolated",     # In-memory profile; no disk state between restarts
                    ],
                }
            }
        )

    async def start(self) -> list[Any]:
        """Spawn MCP subprocess and load tools. Raises RuntimeError on failure."""
        self._client = self._make_client()
        try:
            # client.session() is an async context manager — enter it here, exit on stop()
            self._session_cm = self._client.session("playwright")
            self._session = await asyncio.wait_for(
                self._session_cm.__aenter__(),
                timeout=MCP_STARTUP_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                "MCP subprocess failed to start within 5 seconds. "
                "Check Node.js and @playwright/mcp installation."
            )
        except Exception as e:
            raise RuntimeError(
                f"MCP subprocess failed to start: {e}. "
                "Check Node.js and @playwright/mcp installation."
            ) from e

        # Load tools from the live session
        from langchain_mcp_adapters.tools import load_mcp_tools
        self._tools = await load_mcp_tools(self._session)
        self._ready = True
        self._restart_count = 0
        return self._tools

    async def stop(self) -> None:
        """Close the MCP session and wait for subprocess to exit."""
        self._ready = False
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass  # Best-effort cleanup
            self._session_cm = None
            self._session = None

    @property
    def tools(self) -> list[Any]:
        return self._tools

    @property
    def ready(self) -> bool:
        return self._ready
```

### Pattern 2: FastAPI Lifespan Integration

```python
# Source: FastAPI lifespan docs + langchain-mcp-adapters v0.2.1 patterns
# main.py (additions to Phase 1 main.py)

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mcp.manager import MCPManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    manager = MCPManager()
    try:
        tools = await manager.start()
    except RuntimeError as e:
        logger.error("ERROR: MCP subprocess failed — check Node.js and @playwright/mcp installation")
        raise  # Hard fail: FastAPI refuses to start

    app.state.mcp_manager = manager
    app.state.mcp_tools = tools

    tool_count = len(tools)
    tool_names = [t.name for t in tools]
    logger.info(f"MCP ready — {tool_count} tools available")
    logger.debug(f"MCP tools: {tool_names}")

    yield

    # === SHUTDOWN ===
    await manager.stop()
    logger.info("MCP subprocess shut down cleanly")


app = FastAPI(title="Property Search Agent", lifespan=lifespan)


@app.get("/health")
async def health(request: Request):
    manager = request.app.state.mcp_manager
    if manager.ready:
        return {"status": "ok", "mcp": "ready"}
    return JSONResponse(
        status_code=200,  # /health always 200; degraded is a status field, not HTTP error
        content={"status": "degraded", "mcp": "down"}
    )


@app.get("/tools")
async def tools(request: Request):
    tool_list = request.app.state.mcp_tools
    return {
        "count": len(tool_list),
        "tools": [{"name": t.name, "description": t.description} for t in tool_list],
    }
```

### Pattern 3: Subprocess Termination (No Zombie Chromium)

The MCP subprocess (`npx @playwright/mcp`) spawns Chromium as a child process. Sending SIGTERM only to the npx process may leave Chromium orphaned.

**The correct pattern:** Use `start_new_session=True` when spawning the subprocess. This creates a new process group. On shutdown, call `os.killpg(os.getpgid(pid), signal.SIGTERM)` to signal the entire group.

`langchain-mcp-adapters` uses the `mcp` SDK's `stdio_client` under the hood, which uses `asyncio.create_subprocess_exec`. To control `start_new_session`, you may need to manage the subprocess directly OR rely on the `session().__aexit__()` to close stdin (which triggers the stdio server to exit gracefully per the MCP spec).

**MCP spec shutdown for stdio (verified from modelcontextprotocol.io):**
1. Client closes stdin to the subprocess
2. Wait for subprocess to exit
3. If not exited in reasonable time → SIGTERM
4. If still not exited → SIGKILL

The `langchain-mcp-adapters` `session().__aexit__()` handles step 1 (closes stdin). Steps 2-4 may need manual implementation if Chromium outlives the session close.

**Verified pattern for cleanup:**
```python
# Source: Python asyncio docs + alexandra-zaharia.github.io subprocess termination guide
import asyncio
import os
import signal

async def terminate_process_group(pid: int, timeout: float = 5.0) -> None:
    """Send SIGTERM to entire process group, escalate to SIGKILL on timeout."""
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        # Wait up to timeout for all processes in the group to exit
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: os.waitpid(-pgid, 0)
            ),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Already dead
    except ProcessLookupError:
        pass  # Already dead
```

**Note for planner:** The `langchain-mcp-adapters` session's `__aexit__` may handle most cleanup. Include a fallback `os.killpg` only if testing shows zombie processes. Verify by checking `ps aux | grep chromium` after server shutdown.

### Pattern 4: Crash Detection and Restart

The context decides: crash = subprocess exits unexpectedly, stdio pipe breaks, or request timeout (10s). The manager must monitor for these.

```python
# Simplified crash detection pattern (planner should implement in MCPManager)
async def call_with_crash_detection(self, coro):
    """Wrap a tool call; detect crash and trigger restart."""
    try:
        return await asyncio.wait_for(coro, timeout=MCP_REQUEST_TIMEOUT)
    except (asyncio.TimeoutError, BrokenPipeError, ConnectionResetError) as e:
        self._ready = False
        # Current request fails — do not retry
        if self._restart_count < MAX_RESTART_ATTEMPTS:
            asyncio.create_task(self._restart())  # Restart for future requests
        raise RuntimeError(f"MCP crashed: {e}") from e

async def _restart(self):
    """Attempt to restart the MCP subprocess."""
    await self.stop()
    try:
        await self.start()
        logger.info(f"MCP restarted (attempt {self._restart_count})")
    except RuntimeError:
        self._restart_count += 1
        logger.error(f"MCP restart failed (attempt {self._restart_count}/{MAX_RESTART_ATTEMPTS})")
        if self._restart_count >= MAX_RESTART_ATTEMPTS:
            logger.error("MCP restart attempts exhausted — MCP is down")
```

### Pattern 5: Startup Timeout with Hard Fail

```python
# Source: Python asyncio docs (asyncio.wait_for pattern)
import asyncio

try:
    await asyncio.wait_for(some_startup_coro(), timeout=5.0)
except asyncio.TimeoutError:
    # Hard fail — raise so FastAPI refuses to start
    raise RuntimeError(
        "MCP subprocess failed to start within 5 seconds. "
        "Check Node.js and @playwright/mcp installation."
    )
```

When `lifespan` raises an exception before `yield`, FastAPI refuses to serve requests. The process exits with a non-zero code. This is the desired hard-fail behavior.

### Anti-Patterns to Avoid

- **Calling `get_tools()` per request:** Spawns a fresh subprocess every time. Use a persistent session stored in `app.state` instead.
- **Using `MultiServerMCPClient` as `async with client:`:** Raises `NotImplementedError` since v0.1.0. Use `client.session("playwright")` instead.
- **Not using `start_new_session=True`:** SIGTERM to the npx process won't reach Chromium children. Either rely on stdin-close (MCP spec) or use `os.killpg`.
- **Using `--browser chrome`:** Requires Google Chrome installed on the system. The default (no `--browser` flag) uses the open-source Chromium downloaded by `npx playwright install chromium`.
- **Omitting `--no-sandbox` in WSL2:** Chromium crashes with SIGTRAP in WSL2 without this flag. The environment is confirmed WSL2 (`6.6.87.2-microsoft-standard-WSL2`).
- **Omitting `--headless`:** Without this flag, Playwright MCP defaults to headed mode (visible browser window). This will fail in WSL2 where there is no display server.
- **Calling `await process.wait()` without `asyncio.wait_for`:** Will hang indefinitely if the process never exits.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP stdio protocol | Custom JSON-RPC handshake over stdin/stdout | `langchain-mcp-adapters` `MultiServerMCPClient` + `session()` | MCP handshake has 3 steps (initialize request, initialize response, initialized notification); version negotiation; capability exchange. All handled by the mcp SDK internals. |
| Tool schema conversion | Parse MCP tool schema → LangChain tool | `load_mcp_tools(session)` from langchain_mcp_adapters | Converts MCP JSON schema to Pydantic models; handles complex arg types |
| Browser automation tools | Implement browser control from scratch | `@playwright/mcp` tools (browser_navigate, browser_snapshot, etc.) | ~20 tools covering navigation, clicking, typing, screenshots, evaluation |
| Process group cleanup | Track child PIDs manually | `start_new_session=True` + `os.killpg` | Automatically groups subprocess and its children; one signal kills all |

**Key insight:** The MCP initialization handshake alone (3-step JSON-RPC exchange with capability negotiation) would be hundreds of lines of error-prone code. `langchain-mcp-adapters` + `mcp` SDK handles this entirely.

---

## Common Pitfalls

### Pitfall 1: `get_tools()` Spawns a New Subprocess Every Call

**What goes wrong:** Code calls `await client.get_tools()` on every request. Each call spawns a new `npx @playwright/mcp` subprocess (with Chromium), waits for initialization, loads tools, then tears down. Server becomes slow and eventually accumulates orphaned Chromium processes.

**Why it happens:** `MultiServerMCPClient.get_tools()` is explicitly documented as stateless: "a new session will be created for each tool call." The ephemeral pattern is correct for per-request scenarios but catastrophic for a long-running server.

**How to avoid:** Use `client.session("playwright")` as a context manager opened once in `lifespan`, stored in `app.state`. Load tools once with `load_mcp_tools(session)`, store in `app.state.mcp_tools`.

**Warning signs:** `ps aux | grep chromium` shows multiple Chromium processes after a few requests. Startup latency of 1-2s per tool call instead of <10ms.

### Pitfall 2: No `--headless` Flag in WSL2

**What goes wrong:** `@playwright/mcp` defaults to headed (visible browser window). In WSL2 without a display server, Chromium fails to launch with a display error.

**Why it happens:** The headed default is correct for desktop Claude; not for a headless server.

**How to avoid:** Always include `--headless` in the subprocess args.

**Warning signs:** `Error: Could not find a display server` or Chromium exits immediately with a non-zero code.

### Pitfall 3: No `--no-sandbox` in WSL2

**What goes wrong:** Chromium crashes with SIGTRAP in WSL2 because Chrome's sandboxing requires kernel features not present in the WSL2 kernel.

**Why it happens:** WSL2's Linux kernel doesn't support the user namespaces required for Chrome's sandbox.

**How to avoid:** Include `--no-sandbox` in the subprocess args. Verified flag name in v0.0.68 (a rename to `--no-chromium-sandbox` was introduced in v0.0.67 and reverted in v0.0.68; current correct name is `--no-sandbox`).

**Warning signs:** Chromium starts then immediately dies. `SIGTRAP` appears in process logs. Issue #883 in playwright-mcp GitHub.

### Pitfall 4: Zombie Chromium After Server Shutdown

**What goes wrong:** After `uvicorn` exits (Ctrl+C or `--reload`), `ps aux | grep chromium` shows Chromium processes still running. Repeated server restarts accumulate zombie processes.

**Why it happens:** Sending SIGTERM only to the Node.js `npx` process doesn't propagate to Chromium which is a child of the Node.js process.

**How to avoid:**
- Rely on `session().__aexit__()` which closes stdin — MCP spec says the server should exit when stdin closes.
- Add a post-shutdown check: if Chromium is still running after 2s, call `os.killpg(pgid, signal.SIGTERM)` then `os.killpg(pgid, signal.SIGKILL)`.
- Use `--isolated` flag so no disk state is left behind even if a process does survive.

**Warning signs:** `ps aux | grep chromium` shows processes after server exit.

### Pitfall 5: Hard Fail Not Triggered Correctly

**What goes wrong:** The lifespan function catches `RuntimeError` from `manager.start()` and logs it but continues past `yield`. FastAPI starts serving requests with no MCP backend.

**Why it happens:** Exception handling in lifespan swallows the error. FastAPI only refuses to start if lifespan raises before `yield`.

**How to avoid:** Let the `RuntimeError` propagate from `lifespan` without catching it. Test with a deliberately broken Node.js path to verify the server exits.

**Warning signs:** Server starts successfully even with Node.js uninstalled.

### Pitfall 6: TestClient Tests Hang on MCP Startup

**What goes wrong:** `pytest` test using `TestClient(app)` as a context manager hangs because `lifespan` tries to spawn `npx @playwright/mcp` (which may not be available in test CI or may be slow).

**Why it happens:** `TestClient` as a context manager runs the full lifespan, including MCP startup.

**How to avoid:**
Option A — Mock the MCPManager in tests:
```python
# tests/test_main.py
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_mcp(monkeypatch):
    mock_manager = MagicMock()
    mock_manager.ready = True
    mock_manager.tools = []
    mock_manager.start = AsyncMock(return_value=[])
    mock_manager.stop = AsyncMock()
    monkeypatch.setattr("mcp.manager.MCPManager", lambda: mock_manager)
    return mock_manager
```
Option B — Feature-flag MCP: read an env var `MCP_ENABLED=false` to skip MCP startup in lifespan.

**Warning signs:** `pytest` hangs for >10 seconds on any test.

### Pitfall 7: `MultiServerMCPClient` Used as `async with client:`

**What goes wrong:** `async with client: ...` raises `NotImplementedError: MultiServerMCPClient cannot be used as an async context manager. Call methods directly...`

**Why it happens:** As of v0.1.0, the `__aenter__` and `__aexit__` methods raise `NotImplementedError`. This is intentional — the client object itself has no lifecycle to manage.

**How to avoid:** Use `client.session("playwright")` which IS an async context manager. Or call `client.get_tools()` directly (but note pitfall 1 above for long-running servers).

**Warning signs:** `NotImplementedError` at server startup.

---

## Code Examples

Verified patterns from official sources:

### MultiServerMCPClient with Stdio Transport
```python
# Source: langchain-mcp-adapters v0.2.1 README + PyPI documentation
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

client = MultiServerMCPClient(
    connections={
        "playwright": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "@playwright/mcp",
                "--headless",
                "--no-sandbox",
                "--isolated",
            ],
        }
    }
)

# Persistent session pattern (correct for long-running server)
async with client.session("playwright") as session:
    tools = await load_mcp_tools(session)
    # tools is list[BaseTool] — LangChain-compatible
```

### MCP Protocol Lifecycle (what happens under the hood)
```
# Source: modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle

Client (Python)              Server (npx @playwright/mcp)
    |                                    |
    |-- initialize request (JSON-RPC) -->|
    |<-- initialize response ------------|
    |-- initialized notification ------->|
    |                                    |
    |      [tools.list, tools.call, etc.]|
    |                                    |
    |-- close stdin -------------------->|
    |<-- subprocess exits ---------------|
```

### Subprocess Cleanup (SIGTERM + SIGKILL escalation)
```python
# Source: Python asyncio docs, MCP spec shutdown protocol
import asyncio
import os
import signal

async def force_kill_process_group(pid: int, timeout: float = 5.0) -> None:
    """
    Terminate entire process group (subprocess + all children).
    Use as fallback if session().__aexit__() doesn't clean up Chromium.
    """
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return  # Already dead

    # Step 1: SIGTERM (graceful)
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    # Step 2: Wait up to timeout
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.1)
        try:
            os.kill(pid, 0)  # Check if still alive
        except ProcessLookupError:
            return  # Gone

    # Step 3: SIGKILL (force)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
```

### `@playwright/mcp` Tool Names (confirmed v0.0.68)
```
Core tools (always available):
  browser_navigate           Navigate to a URL
  browser_navigate_back      Browser back button
  browser_snapshot           Get accessibility snapshot of current page
  browser_click              Click an element
  browser_type               Type into a field
  browser_fill_form          Fill a form field
  browser_press_key          Press a keyboard key
  browser_hover              Hover over an element
  browser_select_option      Select from a dropdown
  browser_drag               Drag an element
  browser_take_screenshot    Capture a screenshot (PNG)
  browser_wait_for           Wait for a condition
  browser_evaluate           Execute JavaScript
  browser_run_code           Run code in the browser
  browser_console_messages   Get console output
  browser_network_requests   Inspect network requests
  browser_file_upload        Handle file upload inputs
  browser_handle_dialog      Handle alert/confirm/prompt dialogs
  browser_tabs               Manage browser tabs
  browser_resize             Resize the browser window
  browser_close              Close the browser
  browser_install            Install Playwright browsers (utility)

Additional capabilities (with --caps vision):
  browser_mouse_click_xy, browser_mouse_drag_xy, etc. (coordinate-based)
```

### Correct `@playwright/mcp` CLI Invocation (v0.0.68)
```bash
# For WSL2 headless server (confirmed flags):
npx @playwright/mcp --headless --no-sandbox --isolated

# WRONG — "chromium" is not a valid --browser value in CLI; omit flag to use default Chromium:
npx @playwright/mcp --browser chromium   # WRONG
npx @playwright/mcp --headless           # CORRECT (uses downloaded Chromium by default)

# Install Chromium browser binary (required before first run):
npx playwright install chromium
```

### FastAPI Health and Tools Endpoints
```python
# Source: FastAPI docs + phase decisions
@app.get("/health")
async def health(request: Request):
    manager: MCPManager = request.app.state.mcp_manager
    if manager.ready:
        return {"status": "ok", "mcp": "ready"}
    return JSONResponse(
        status_code=200,
        content={"status": "degraded", "mcp": "down"}
    )

@app.get("/tools")
async def list_tools(request: Request):
    tools = request.app.state.mcp_tools
    return {
        "count": len(tools),
        "tools": [{"name": t.name, "description": t.description} for t in tools],
    }
```

---

## State of the Art (February 2026)

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `async with MultiServerMCPClient(...) as client:` | `client.session("server_name")` as the context manager | v0.1.0 of langchain-mcp-adapters | `__aenter__` raises `NotImplementedError`; must use `session()` |
| `--no-chromium-sandbox` flag | `--no-sandbox` flag | @playwright/mcp v0.0.68 (Feb 14, 2026) | v0.0.67 renamed; v0.0.68 reverted; current correct name is `--no-sandbox` |
| `--browser chromium` in CLI | Omit `--browser` entirely (uses downloaded Chromium by default) | Always | CLI accepts `chrome, firefox, webkit, msedge`; "chromium" is only valid in config file schema |
| `@app.on_event("startup")` | `@asynccontextmanager lifespan` | FastAPI 0.93+ | Still applies — Phase 2 continues Phase 1 pattern |
| `client.get_tools()` per request | Persistent `session()` + cached tools in `app.state` | v0.1.0+ semantics clarified | `get_tools()` is ephemeral; session is persistent |

**Deprecated/outdated:**
- `async with MultiServerMCPClient(...):` — raises `NotImplementedError`, use `client.session()`.
- `--no-chromium-sandbox` — use `--no-sandbox` in v0.0.68+.
- Spawning subprocesses with `subprocess.Popen` (sync) in async FastAPI — use `asyncio.create_subprocess_exec`.

---

## Open Questions

1. **Does `session().__aexit__()` fully clean up Chromium?**
   - What we know: MCP spec says closing stdin should cause the server to exit. The `mcp` SDK's stdio transport likely closes stdin on session exit.
   - What's unclear: Whether all Chromium child processes exit when the Node.js parent's stdin closes, or whether some linger.
   - Recommendation: Implement the session `__aexit__` first; verify with `ps aux | grep chromium` after shutdown. Add `os.killpg` fallback if zombies are observed during testing.

2. **Does `load_mcp_tools(session)` work, or is the correct API `await client.get_tools(server_name="playwright")`?**
   - What we know: `load_mcp_tools` is exported from `langchain_mcp_adapters.tools`. `get_tools()` is a convenience method on the client. Both should work with a session.
   - What's unclear: The exact import path for `load_mcp_tools` in v0.2.1.
   - Recommendation: Try `from langchain_mcp_adapters.tools import load_mcp_tools` first; fall back to verifying from source if the import fails.

3. **Restart counter increment logic**
   - What we know: Decisions say "up to 3 restart attempts before giving up."
   - What's unclear: Whether the counter resets on successful restart (allowing future crashes to attempt 3 more restarts) or is lifetime-capped at 3.
   - Recommendation: Reset to 0 on successful restart. This gives 3 attempts per crash event, which is more resilient.

4. **Chromium installation check timing**
   - What we know: First startup requires `npx playwright install chromium`. Context marks this as Claude's Discretion.
   - What's unclear: Whether to auto-run `npx playwright install chromium` at startup or require it as a manual prereq.
   - Recommendation: Check if Chromium is already installed (check `~/.cache/ms-playwright/`). If not, run `npx playwright install chromium` automatically during startup (this is a one-time operation; add a log warning: `Chromium not found, downloading...`).

---

## Sources

### Primary (HIGH confidence)
- `npx @playwright/mcp --help` — live output, confirmed v0.0.68, all flags verified
- `npm show @playwright/mcp version` — confirmed v0.0.68, dist-tags `latest: 0.0.68`
- `npm show @playwright/mcp dist-tags` — confirmed `next: 0.0.68-alpha-2026-02-19`
- Python asyncio subprocess docs (docs.python.org/3/library/asyncio-subprocess.html) — `create_subprocess_exec`, `Process.terminate()`, `Process.kill()`, `asyncio.wait_for`
- modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle — MCP initialization handshake, stdio shutdown protocol (close stdin → SIGTERM → SIGKILL)
- PyPI langchain-mcp-adapters 0.2.1 — version confirmed, dependencies: `mcp>=1.9.2`, `langchain-core>=1.0.0`

### Secondary (MEDIUM confidence)
- GitHub microsoft/playwright-mcp releases — changelog for v0.0.60–0.0.68 (--no-sandbox revert confirmed)
- DeepWiki langchain-ai/langchain-mcp-adapters/8.1-client-api — `get_tools()` ephemeral behavior, `session()` API, `__aenter__` NotImplementedError
- DeepWiki langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient — constructor signature, persistent vs ephemeral sessions
- GitHub microsoft/playwright-mcp issue #883 (WSL2 SIGTRAP, resolved in v0.35, --no-sandbox required)
- playwright-mcp README (raw.githubusercontent.com) — CLI invocation, tool names list, browser options

### Tertiary (LOW confidence, flag for validation)
- Tool names list from executeautomation.github.io/mcp-playwright — may differ from microsoft/playwright-mcp; verify with `GET /tools` at startup
- `load_mcp_tools` import path — not directly verified from source; inferred from DeepWiki + README examples

---

## Metadata

**Confidence breakdown:**
- Standard stack versions: HIGH — npm confirmed @playwright/mcp 0.0.68, PyPI confirmed langchain-mcp-adapters 0.2.1, Node.js v18.20.8 confirmed on system
- Architecture (persistent session pattern): HIGH — verified from langchain-mcp-adapters source analysis + DeepWiki documentation
- `get_tools()` ephemeral behavior: HIGH — explicitly documented + confirmed from multiple sources
- `--no-sandbox` WSL2 requirement: HIGH — confirmed from playwright-mcp issue #883 (closed/resolved), verified flag name in v0.0.68 help output
- `--headless` requirement: HIGH — help output confirms "headed by default"; WSL2 has no display
- `--browser chromium` is WRONG: HIGH — help output lists valid values as `chrome, firefox, webkit, msedge`; "chromium" is not in the CLI list
- MCP protocol handshake: HIGH — official MCP spec
- Tool names: MEDIUM — extracted from README and executeautomation docs; exact list validated at runtime via `GET /tools`
- `load_mcp_tools` import path: MEDIUM — inferred, not directly verified from installed source

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (30 days; `@playwright/mcp` is fast-moving, currently at 0.0.68 with frequent releases)
