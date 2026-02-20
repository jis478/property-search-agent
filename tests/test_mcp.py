import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_subprocess.manager import MCPManager


@pytest.mark.asyncio
async def test_start_raises_on_timeout():
    """If MCP session init times out, start() raises RuntimeError."""
    manager = MCPManager()

    async def slow_aenter(*args, **kwargs):
        await asyncio.sleep(10)  # Exceeds MCP_STARTUP_TIMEOUT

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = slow_aenter

    mock_client = MagicMock()
    mock_client.session.return_value = mock_session_cm

    with patch.object(manager, "_make_client", return_value=mock_client), \
         patch.object(manager, "_ensure_chromium", new=AsyncMock()), \
         patch("mcp_subprocess.manager.MCP_STARTUP_TIMEOUT", 0.05):
        with pytest.raises(RuntimeError, match="MCP subprocess failed"):
            await manager.start()


@pytest.mark.asyncio
async def test_start_raises_on_exception():
    """If MCP session init raises, start() wraps and raises RuntimeError."""
    manager = MCPManager()

    async def failing_aenter(*args, **kwargs):
        raise OSError("npx not found")

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = failing_aenter

    mock_client = MagicMock()
    mock_client.session.return_value = mock_session_cm

    with patch.object(manager, "_make_client", return_value=mock_client), \
         patch.object(manager, "_ensure_chromium", new=AsyncMock()):
        with pytest.raises(RuntimeError, match="MCP subprocess failed"):
            await manager.start()


@pytest.mark.asyncio
async def test_start_sets_ready():
    """After a successful start(), ready is True and tools is populated."""
    manager = MCPManager()

    mock_tool = MagicMock()
    mock_tool.name = "browser_navigate"
    mock_tool.description = "Navigate"

    mock_session = MagicMock()

    async def fast_aenter(*args, **kwargs):
        return mock_session

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = fast_aenter
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.session.return_value = mock_session_cm

    with patch.object(manager, "_make_client", return_value=mock_client), \
         patch.object(manager, "_ensure_chromium", new=AsyncMock()), \
         patch("mcp_subprocess.manager.load_mcp_tools", AsyncMock(return_value=[mock_tool])):
        tools = await manager.start()

    assert manager.ready is True
    assert len(tools) == 1
    assert tools[0].name == "browser_navigate"


@pytest.mark.asyncio
async def test_stop_sets_not_ready():
    """stop() sets ready to False."""
    manager = MCPManager()
    manager._ready = True  # simulate a running manager

    mock_session_cm = MagicMock()
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    manager._session_cm = mock_session_cm

    # Patch asyncio.sleep and subprocess calls so stop() completes quickly
    with patch("mcp_subprocess.manager.asyncio.sleep", new=AsyncMock()), \
         patch("mcp_subprocess.manager.subprocess.run", return_value=MagicMock(returncode=1)):
        await manager.stop()

    assert manager.ready is False
