---
phase: 02-mcp-integration
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - mcp/manager.py
  - mcp/__init__.py
  - main.py
autonomous: true
requirements:
  - SCRP-01

must_haves:
  truths:
    - "FastAPI starts only when the @playwright/mcp subprocess starts successfully within 5 seconds"
    - "FastAPI refuses to start (process exits non-zero) if MCP subprocess fails or times out"
    - "GET /health returns {status: ok, mcp: ready} when MCP is running"
    - "GET /health returns {status: degraded, mcp: down} when MCP has crashed and restart failed"
    - "GET /tools returns a JSON list of all MCP tool names and descriptions"
    - "Stopping the FastAPI server terminates the MCP subprocess and Chromium children without leaving zombies"
    - "The MCP subprocess auto-restarts (up to 3 attempts) after a crash; future requests work again after recovery"
  artifacts:
    - path: "mcp/manager.py"
      provides: "MCPManager class with start(), stop(), tools, ready properties and crash-restart logic"
      contains: "class MCPManager"
    - path: "main.py"
      provides: "Updated lifespan wiring MCPManager, enhanced /health, new /tools endpoint"
      contains: "GET /tools"
    - path: "requirements.txt"
      provides: "langchain-mcp-adapters dependency"
      contains: "langchain-mcp-adapters"
  key_links:
    - from: "main.py lifespan"
      to: "mcp/manager.py MCPManager.start()"
      via: "await manager.start() in asynccontextmanager"
      pattern: "await manager\\.start\\(\\)"
    - from: "main.py /health"
      to: "app.state.mcp_manager.ready"
      via: "request.app.state.mcp_manager"
      pattern: "mcp_manager\\.ready"
    - from: "main.py /tools"
      to: "app.state.mcp_tools"
      via: "request.app.state.mcp_tools"
      pattern: "mcp_tools"
    - from: "mcp/manager.py MCPManager"
      to: "langchain_mcp_adapters.client.MultiServerMCPClient"
      via: "client.session('playwright') persistent context manager"
      pattern: "client\\.session\\(\"playwright\"\\)"
---

<objective>
Implement the MCPManager subprocess lifecycle class and wire it into the FastAPI lifespan, health endpoint, and a new /tools endpoint.

Purpose: This is the core infrastructure of Phase 2. Without a running, managed MCP subprocess, the LangGraph agent (Phase 3) has no browser tools to call. Getting startup, shutdown, and crash recovery right here prevents zombie Chromium processes and ensures reliable operation across server restarts.

Output: mcp/manager.py (MCPManager class), updated main.py (lifespan + /health + /tools), updated requirements.txt
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-mcp-integration/02-CONTEXT.md
@.planning/phases/02-mcp-integration/02-RESEARCH.md
@.planning/phases/01-foundation/01-foundation-01-SUMMARY.md
@main.py
@mcp/__init__.py
@requirements.txt
</context>

<tasks>

<task type="auto">
  <name>Task 1: MCPManager class and requirements update</name>
  <files>mcp/manager.py, mcp/__init__.py, requirements.txt</files>
  <action>
Add `langchain-mcp-adapters>=0.2.1,<0.3` to requirements.txt and install it.

Create `mcp/manager.py` with the `MCPManager` class. Install the dependency first:

```bash
pip install "langchain-mcp-adapters>=0.2.1,<0.3"
```

Then verify the import path for load_mcp_tools is correct (check the installed package):
```bash
python3 -c "from langchain_mcp_adapters.tools import load_mcp_tools; print('OK')"
```

If the import fails, try:
```bash
python3 -c "from langchain_mcp_adapters.client import MultiServerMCPClient; help(MultiServerMCPClient.get_tools)"
```
and adjust accordingly — the research notes MEDIUM confidence on the load_mcp_tools import path.

Implement MCPManager with these constants and behaviours:
- `MCP_STARTUP_TIMEOUT = 5.0` (seconds, hard fail per CONTEXT.md)
- `MCP_REQUEST_TIMEOUT = 10.0` (seconds, crash threshold per CONTEXT.md)
- `MAX_RESTART_ATTEMPTS = 3`

The subprocess command: `npx @playwright/mcp --headless --no-sandbox --isolated`
- `--headless`: required — WSL2 has no display server
- `--no-sandbox`: required — WSL2 kernel lacks Chrome sandbox support (SIGTRAP without it)
- `--isolated`: in-memory profile, no disk state between restarts
- Do NOT pass `--browser chromium` — "chromium" is not a valid CLI value; omit to use downloaded Chromium

**`MCPManager` interface:**
- `__init__`: initialise `_client`, `_session_cm`, `_session`, `_tools`, `_restart_count`, `_ready` to None/empty/False
- `_make_client() -> MultiServerMCPClient`: construct `MultiServerMCPClient` with the stdio connection dict
- `start() -> list[BaseTool]`: open the persistent session using `client.session("playwright")` (an async context manager — store `_session_cm` and enter it with `__aenter__`), wrap in `asyncio.wait_for(..., timeout=MCP_STARTUP_TIMEOUT)`. If `TimeoutError` or any `Exception`, raise `RuntimeError` with message: `"MCP subprocess failed — check Node.js and @playwright/mcp installation"`. After success: call `load_mcp_tools(self._session)` (or the equivalent confirmed import), store in `self._tools`, set `self._ready = True`, reset `self._restart_count = 0`. Return `self._tools`.
- `stop()`: set `self._ready = False`, call `await self._session_cm.__aexit__(None, None, None)` in a try/except (best-effort), set `_session_cm = _session = None`. After session exit, verify Chromium is gone — wait 2 seconds, then check if any `chromium` processes remain. If they do, call a `_force_kill_chromium()` helper that reads the process list and sends SIGKILL to any `chromium` processes (using `subprocess.run(["pkill", "-9", "-f", "chromium"])` as a last resort).
- `tools` property: returns `self._tools`
- `ready` property: returns `self._ready`
- `_restart()` async: call `stop()`, then `start()`. If start succeeds, log `INFO: MCP restarted (attempt {n})`. If start raises, increment `self._restart_count`, log `ERROR: MCP restart {n}/{MAX} failed`. If count >= MAX_RESTART_ATTEMPTS after failure, log `ERROR: MCP restart attempts exhausted — MCP is down`.
- `call_with_crash_detection(coro)` async: wrap `await asyncio.wait_for(coro, timeout=MCP_REQUEST_TIMEOUT)`. On `asyncio.TimeoutError`, `BrokenPipeError`, or `ConnectionResetError`: set `self._ready = False`, if `self._restart_count < MAX_RESTART_ATTEMPTS` schedule `asyncio.create_task(self._restart())` for future requests. Raise `RuntimeError(f"MCP tool call failed: {e}")` — current request always fails, never silent retry.

Update `mcp/__init__.py` to export `MCPManager`:
```python
from mcp.manager import MCPManager

__all__ = ["MCPManager"]
```

Also check if Chromium is already installed at startup: `_make_client()` or `start()` should check whether `~/.cache/ms-playwright/chromium-*/chrome-linux/chrome` exists (use `Path.home() / ".cache" / "ms-playwright"`). If no chromium directory found, run `npx playwright install chromium` via `asyncio.create_subprocess_exec` with `await proc.wait()` before attempting to start the MCP session. Log: `WARNING: Chromium not found — downloading via npx playwright install chromium (this may take a minute)`.
  </action>
  <verify>
```bash
cd /home/mark/hobby
python3 -c "from mcp.manager import MCPManager; m = MCPManager(); print('MCPManager imports OK')"
python3 -c "from langchain_mcp_adapters.client import MultiServerMCPClient; print('MCP adapter imports OK')"
grep "langchain-mcp-adapters" requirements.txt
```
All three commands succeed with no errors.
  </verify>
  <done>
`MCPManager` class exists in mcp/manager.py and imports without error. `langchain-mcp-adapters` is in requirements.txt and installed. `mcp/__init__.py` exports MCPManager. The class has `start()`, `stop()`, `tools`, `ready`, `call_with_crash_detection()`, and `_restart()` implemented.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire MCPManager into FastAPI lifespan, /health, and /tools</name>
  <files>main.py</files>
  <action>
Update `main.py` to integrate MCPManager into the lifespan context manager and add the /health and /tools endpoints. Replace the existing stub lifespan with a real implementation.

**Lifespan implementation (hard fail on startup):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    manager = MCPManager()
    try:
        tools = await manager.start()
    except RuntimeError as e:
        logger.error(f"ERROR: MCP subprocess failed — check Node.js and @playwright/mcp installation")
        raise  # Hard fail: FastAPI refuses to start; process exits non-zero

    app.state.mcp_manager = manager
    app.state.mcp_tools = tools

    tool_names = [t.name for t in tools]
    logger.info(f"MCP ready — {len(tools)} tools available")
    logger.debug(f"MCP tools: {tool_names}")

    yield

    # === SHUTDOWN ===
    await manager.stop()
    logger.info("MCP subprocess shut down cleanly")
```

The `raise` after `logger.error` is critical — do NOT catch and swallow the error. When lifespan raises before `yield`, FastAPI refuses to serve requests and the process exits with a non-zero code. This is the intended hard-fail behaviour.

**Update /health endpoint** (was `{"status": "ok"}`, now MCP-aware):
```python
@app.get("/health")
async def health(request: Request):
    manager: MCPManager = request.app.state.mcp_manager
    if manager.ready:
        return {"status": "ok", "mcp": "ready"}
    return JSONResponse(
        status_code=200,  # always 200 — degraded is a status field, not HTTP 5xx
        content={"status": "degraded", "mcp": "down"}
    )
```

Note: The existing `test_health` test asserts `{"status": "ok"}` — this will break. That's fine; the test will be fixed in Plan 02. Do not special-case the health endpoint for tests here.

**Add /tools endpoint** (new):
```python
@app.get("/tools")
async def list_tools(request: Request):
    tool_list = request.app.state.mcp_tools
    return {
        "count": len(tool_list),
        "tools": [{"name": t.name, "description": t.description} for t in tool_list],
    }
```

**Required imports to add to main.py:**
- `import logging`
- `from fastapi.responses import JSONResponse`
- `from mcp.manager import MCPManager`

Add `logger = logging.getLogger(__name__)` at module level.

Keep all existing imports and the existing `GET /` route unchanged.
  </action>
  <verify>
```bash
cd /home/mark/hobby
python3 -c "import ast; ast.parse(open('main.py').read()); print('main.py parses OK')"
grep -n "MCPManager\|/tools\|/health\|mcp_manager\|JSONResponse" main.py
```
main.py parses without syntax error. grep shows MCPManager import, /tools route, and JSONResponse usage all present.
  </verify>
  <done>
main.py has updated lifespan calling `manager.start()` with hard-fail on RuntimeError, stores `app.state.mcp_manager` and `app.state.mcp_tools`, has MCP-aware `/health` returning `{status, mcp}` fields, and has new `/tools` endpoint returning `{count, tools: [{name, description}]}`. The existing `GET /` route is unmodified.
  </done>
</task>

</tasks>

<verification>
Full integration check — start the server and verify the MCP subprocess actually connects:

```bash
cd /home/mark/hobby
# Verify Chromium is installed (required before server start)
ls ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome 2>/dev/null && echo "Chromium present" || echo "Chromium missing — run: npx playwright install chromium"

# Start server (if Chromium present)
uvicorn main:app --host 127.0.0.1 --port 8000 &
sleep 8  # MCP needs up to 5s to start

# Verify health endpoint
curl -s http://127.0.0.1:8000/health
# Expected: {"status":"ok","mcp":"ready"}

# Verify tools endpoint
curl -s http://127.0.0.1:8000/tools | python3 -m json.tool | head -20
# Expected: {"count": N, "tools": [...]} where N > 0

# Verify zombie-free shutdown
kill %1
sleep 3
ps aux | grep -i chromium | grep -v grep && echo "WARNING: zombie chromium" || echo "Clean shutdown confirmed"
```
</verification>

<success_criteria>
1. `MCPManager` class exists in `mcp/manager.py`, imports cleanly, has all required methods and properties.
2. `requirements.txt` contains `langchain-mcp-adapters>=0.2.1,<0.3` and it is pip-installed.
3. `main.py` lifespan calls `manager.start()`, hard-fails on RuntimeError (raises before yield), stores `app.state.mcp_manager` and `app.state.mcp_tools`.
4. `GET /health` returns `{"status": "ok", "mcp": "ready"}` when MCP is running.
5. `GET /tools` returns `{"count": N, "tools": [...]}` with at least 1 tool when MCP is running.
6. After server shutdown (`kill`), no Chromium processes remain in `ps aux`.
7. `python3 -c "import ast; ast.parse(open('main.py').read())"` and `python3 -c "from mcp.manager import MCPManager"` both succeed.
</success_criteria>

<output>
After completion, create `.planning/phases/02-mcp-integration/02-mcp-integration-01-SUMMARY.md` following the summary template.
</output>