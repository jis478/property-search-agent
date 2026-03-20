import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import api.search as search_module
from main import app


@pytest.fixture(autouse=True)
def clear_run_store():
    """Reset run_store and _current_run_id between tests."""
    search_module.run_store.clear()
    search_module._current_run_id = None
    yield
    search_module.run_store.clear()
    search_module._current_run_id = None


@pytest.fixture
def mock_mcp(monkeypatch):
    mock_manager = MagicMock()
    mock_manager.ready = True
    mock_manager.start = AsyncMock(return_value=[])
    mock_manager.stop = AsyncMock()
    monkeypatch.setattr("main.MCPManager", lambda: mock_manager)
    return mock_manager


@pytest.fixture
def mock_agent(monkeypatch):
    """Mock build_agent so lifespan does not try to build a real LangGraph agent."""
    fake_agent = MagicMock()
    monkeypatch.setattr("main.build_agent", lambda tools: fake_agent)
    return fake_agent


def test_post_search_returns_run_id(mock_mcp, mock_agent):
    with TestClient(app) as client:
        response = client.post("/search", json={"query": "3 bed house in Richmond VIC"})
    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert len(data["run_id"]) == 36  # UUID4 string


def test_post_search_creates_run_in_store(mock_mcp, mock_agent):
    with TestClient(app) as client:
        response = client.post("/search", json={"query": "test query"})
    run_id = response.json()["run_id"]
    assert run_id in search_module.run_store
    run = search_module.run_store[run_id]
    assert run["query"] == "test query"
    assert run["status"] in ("pending", "running", "complete", "error")


def test_post_search_409_when_run_active(mock_mcp, mock_agent):
    # Manually set an active run_id
    search_module._current_run_id = "existing-run-id"
    with TestClient(app) as client:
        response = client.post("/search", json={"query": "another query"})
    assert response.status_code == 409
    assert "already in progress" in response.json()["detail"].lower()


def test_post_search_missing_query(mock_mcp, mock_agent):
    with TestClient(app) as client:
        response = client.post("/search", json={})
    assert response.status_code == 422  # Pydantic validation error
