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


@pytest.fixture
def mock_agent(monkeypatch):
    """Mock build_agent so lifespan does not try to build a real LangGraph agent."""
    fake_agent = MagicMock()
    monkeypatch.setattr("main.build_agent", lambda tools: fake_agent)
    return fake_agent


def test_health_ok(mock_mcp, mock_agent):
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mcp"] == "ready"


def test_health_degraded(mock_mcp, mock_agent):
    mock_mcp.ready = False
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["mcp"] == "down"


def test_tools_endpoint(mock_mcp, mock_agent):
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


def test_index_returns_html(mock_mcp, mock_agent):
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
