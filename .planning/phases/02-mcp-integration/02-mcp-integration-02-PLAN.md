---
phase: 02-mcp-integration
plan: 02
type: execute
wave: 2
depends_on:
  - 02-mcp-integration-01
files_modified:
  - tests/test_main.py
  - tests/test_mcp.py
autonomous: true
requirements:
  - SCRP-01

must_haves:
  truths:
    - "pytest passes for all existing and new tests without spawning a real MCP subprocess"
    - "The mocked /health test asserts the new {status, mcp} response shape"
    - "A test verifies that /tools returns {count, tools} when MCPManager is mocked as ready"
    - "A test verifies that /health returns degraded when MCPManager is mocked as not ready"
    - "A test verifies that MCPManager.start() raises RuntimeError when the session times out"
  artifacts:
    - path: "tests/test_main.py"
      provides: "Updated tests with MCPManager mock fixture; existing tests adapted to new /health shape"
      contains: "mock_mcp"
    - path: "tests/test_mcp.py"
      provides: "Unit tests for MCPManager startup failure and health/tools endpoint contracts"
      contains: "test_health_degraded"
  key_links:
    - from: "tests/test_main.py mock_mcp fixture"
      to: "mcp.manager.MCPManager"
      via: "monkeypatch.setattr on MCPManager"
      pattern: "monkeypatch\\.setattr.*MCPManager"
    - from: "TestClient(app)"
      to: "app lifespan"
      via: "context manager — triggers lifespan startup/shutdown"
      pattern: "with TestClient\\(app\\)"
---

<objective>
Update existing tests to work with the MCP-aware FastAPI app and add focused tests for the new /health and /tools endpoints and MCPManager failure behaviour.

Purpose: The Phase 1 tests currently use a stub lifespan. Phase 2's lifespan tries to spawn a real MCP subprocess — which would make tests hang or fail in CI without Node.js/@playwright/mcp. Tests must mock the MCPManager to stay fast and hermetic. Without this plan, the test suite is broken.

Output: Updated tests/test_main.py, new tests/test_mcp.py
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
@.planning/phases/02-mcp-integration/02-mcp-integration-01-SUMMARY.md
@tests/test_main.py
@main.py
@mcp/manager.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update test_main.py with MCPManager mock fixture</name>
  <files>tests/test_main.py</files>
  <action>
Rewrite `tests/test_main.py` to add a `mock_mcp` pytest fixture that patches MCPManager so the lifespan never tries to spawn a real subprocess. All tests must use this fixture.

The fixture must patch at the point of import in `main.py` — that is, `main.MCPManager` (not `mcp.manager.MCPManager`) — because `main.py` imports `MCPManager` directly, and monkeypatch must replace the name as seen by the lifespan.

**mock_mcp fixture:**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def mock_mcp(monkeypatch):
    mock_manager = MagicMock()
    mock_manager.ready = True
    mock_manager.tools = []
    mock_manager.start = AsyncMock(return_value=[])
    mock_manager.stop = AsyncMock()

    # Patch the MCPManager class in main.py's namespace
    # so lifespan instantiates our mock instead of the real class
    monkeypatch.setattr("main.MCPManager", lambda: mock_manager)
    return mock_manager
```

**Updated tests (all require mock_mcp fixture):**

`test_health_ok` — replaces old `test_health`:
```python
def test_health_ok(mock_mcp):
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mcp"] == "ready"
```

`test_health_degraded` — new test, mock manager is not ready:
```python
def test_health_degraded(mock_mcp):
    mock_mcp.ready = False
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["mcp"] == "down"
```

`test_tools_endpoint` — new test:
```python
def test_tools_endpoint(mock_mcp):
    # Give the mock some tools
    tool_a = MagicMock()
    tool_a.name = "browser_navigate"
    tool_a.description = "Navigate to a URL"
    tool_b = MagicMock()
    tool_b.name = "browser_snapshot"
    tool_b.description = "Get accessibility snapshot"
    mock_mcp.tools = [tool_a, tool_b]
    mock_mcp.start = AsyncMock(return_value=[tool_a, tool_b])

    with TestClient(app) as client:
        response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert any(t["name"] == "browser_navigate" for t in data["tools"])
```

`test_index_returns_html` — unchanged logic, just add fixture:
```python
def test_index_returns_html(mock_mcp):
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
```

Remove the old `test_health` function entirely (replaced by `test_health_ok`).

The mock fixture works because: the lifespan calls `manager = MCPManager()` — after monkeypatching `main.MCPManager` to `lambda: mock_manager`, this call returns `mock_manager`. Then `await manager.start()` calls `mock_manager.start()` which is an `AsyncMock` returning `[]`. The lifespan stores the mock in `app.state.mcp_manager` and the empty list in `app.state.mcp_tools`. Tests run without spawning any subprocess.
  </action>
  <verify>
```bash
cd /home/mark/hobby
python3 -m pytest tests/test_main.py -v 2>&1 | tail -20
```
All 4 tests pass. No test takes more than 5 seconds. Output shows `4 passed`.
  </verify>
  <done>
`tests/test_main.py` has 4 tests: `test_health_ok`, `test_health_degraded`, `test_tools_endpoint`, `test_index_returns_html`. All use `mock_mcp` fixture. `python3 -m pytest tests/test_main.py -v` reports `4 passed` with no warnings about skipped or hanging tests.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add MCPManager unit tests in test_mcp.py</name>
  <files>tests/test_mcp.py</files>
  <action>
Create `tests/test_mcp.py` with focused unit tests for the MCPManager class itself — specifically startup failure behaviour (the hard-fail contract) and the crash-detection state transitions. Do NOT test the full subprocess integration here (that requires a live Node.js environment and belongs in manual verification).

**Test: startup raises RuntimeError on timeout**
```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.manager import MCPManager


@pytest.mark.asyncio
async def test_start_raises_on_timeout():
    """If MCP session init times out, start() raises RuntimeError."""
    manager = MCPManager()

    async def slow_aenter():
        await asyncio.sleep(10)  # Exceeds MCP_STARTUP_TIMEOUT

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = slow_aenter

    mock_client = MagicMock()
    mock_client.session.return_value = mock_session_cm

    with patch.object(manager, "_make_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="MCP subprocess failed"):
            await manager.start()
```

**Test: start() raises RuntimeError on any exception from session init**
```python
@pytest.mark.asyncio
async def test_start_raises_on_exception():
    """If MCP session init raises, start() wraps and raises RuntimeError."""
    manager = MCPManager()

    async def failing_aenter():
        raise OSError("npx not found")

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = failing_aenter

    mock_client = MagicMock()
    mock_client.session.return_value = mock_session_cm

    with patch.object(manager, "_make_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="MCP subprocess failed"):
            await manager.start()
```

**Test: after successful start, ready is True**
```python
@pytest.mark.asyncio
async def test_start_sets_ready():
    """After a successful start(), ready is True and tools is populated."""
    manager = MCPManager()

    mock_tool = MagicMock()
    mock_tool.name = "browser_navigate"
    mock_tool.description = "Navigate"

    async def fast_aenter():
        return MagicMock()  # mock session

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = fast_aenter
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.session.return_value = mock_session_cm

    with patch.object(manager, "_make_client", return_value=mock_client):
        with patch("mcp.manager.load_mcp_tools", AsyncMock(return_value=[mock_tool])):
            tools = await manager.start()

    assert manager.ready is True
    assert len(tools) == 1
    assert tools[0].name == "browser_navigate"
```

**Test: stop() sets ready to False**
```python
@pytest.mark.asyncio
async def test_stop_sets_not_ready():
    """stop() sets ready to False."""
    manager = MCPManager()
    manager._ready = True  # simulate a running manager

    mock_session_cm = MagicMock()
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    manager._session_cm = mock_session_cm

    await manager.stop()

    assert manager.ready is False
```

**Install pytest-asyncio for async tests:**
Add `pytest-asyncio>=0.24,<1` to `requirements-dev.txt` and install it:
```bash
pip install "pytest-asyncio>=0.24,<1"
```

Add `pytest.ini` or `pyproject.toml` asyncio mode configuration. Since the project has no pyproject.toml, create a `pytest.ini` in the project root:
```ini
[pytest]
asyncio_mode = auto
```

This avoids needing `@pytest.mark.asyncio` on every test (but include it anyway for explicitness since the research-recommended pattern uses it).

If `pytest.ini` already exists, add `asyncio_mode = auto` to it. Check first with `ls /home/mark/hobby/pytest.ini`.

Note on `load_mcp_tools` import path: The test patches `mcp.manager.load_mcp_tools`. If the actual import in `mcp/manager.py` differs (e.g., inline import or different path), adjust the patch target to match the actual import location — always patch where the name is looked up, not where it's defined.
  </action>
  <verify>
```bash
cd /home/mark/hobby
python3 -m pytest tests/test_mcp.py -v 2>&1 | tail -20
python3 -m pytest tests/ -v 2>&1 | tail -10
```
`tests/test_mcp.py` shows 4 passed. Full suite shows all tests pass (6+ total). No asyncio warnings or errors.
  </verify>
  <done>
`tests/test_mcp.py` exists with 4 async tests covering: startup timeout raises RuntimeError, startup exception raises RuntimeError, successful start sets ready=True, stop sets ready=False. `pytest-asyncio` is in requirements-dev.txt and installed. `pytest.ini` has `asyncio_mode = auto`. Full `python3 -m pytest tests/ -v` run passes all tests.
  </done>
</task>

</tasks>

<verification>
Run the complete test suite to confirm everything passes together:

```bash
cd /home/mark/hobby
python3 -m pytest tests/ -v
```

Expected output: All tests pass. No tests hang (all complete in under 10 seconds total). No deprecation warnings about async fixtures.

Also confirm no import errors in any module:
```bash
python3 -c "from mcp.manager import MCPManager; from main import app; print('All imports OK')"
```
</verification>

<success_criteria>
1. `python3 -m pytest tests/ -v` reports all tests passed (minimum 6 tests across both files).
2. No test takes longer than 5 seconds — all MCP subprocess calls are mocked.
3. `test_health_ok` asserts `{"status": "ok", "mcp": "ready"}`.
4. `test_health_degraded` asserts `{"status": "degraded", "mcp": "down"}` when `manager.ready = False`.
5. `test_tools_endpoint` asserts `{"count": 2, "tools": [...]}` with named tools.
6. `tests/test_mcp.py` has async tests covering startup timeout, startup exception, ready state after start, and not-ready state after stop.
7. pytest-asyncio is installed and `asyncio_mode = auto` is configured.
</success_criteria>

<output>
After completion, create `.planning/phases/02-mcp-integration/02-mcp-integration-02-SUMMARY.md` following the summary template.
</output>