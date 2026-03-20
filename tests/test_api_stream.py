import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import api.search as search_module
from main import app


@pytest.fixture(autouse=True)
def clear_run_store():
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
    fake_agent = MagicMock()
    monkeypatch.setattr("main.build_agent", lambda tools: fake_agent)
    return fake_agent


def test_stream_404_for_unknown_run_id(mock_mcp, mock_agent):
    with TestClient(app) as client:
        response = client.get("/stream/nonexistent-run-id")
    assert response.status_code == 404


def test_stream_sse_content_type(mock_mcp, mock_agent):
    """GET /stream/{run_id} must return Content-Type: text/event-stream."""
    # Pre-populate a completed run with a sentinel already on the queue
    loop = asyncio.new_event_loop()
    queue = asyncio.Queue()
    # Put sentinel immediately so generator exits right away
    loop.run_until_complete(queue.put(None))
    loop.close()

    run_id = "test-run-123"
    search_module.run_store[run_id] = {
        "status": "complete",
        "queue": queue,
        "task": None,
        "query": "test",
    }

    with TestClient(app) as client:
        response = client.get(f"/stream/{run_id}")
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_stream_emits_event_then_closes(mock_mcp, mock_agent):
    """SSE generator emits a thinking event then stops on sentinel."""
    loop = asyncio.new_event_loop()
    queue = asyncio.Queue()
    loop.run_until_complete(queue.put({"type": "thinking", "text": "Hello"}))
    loop.run_until_complete(queue.put(None))  # sentinel
    loop.close()

    run_id = "test-run-456"
    search_module.run_store[run_id] = {
        "status": "running",
        "queue": queue,
        "task": None,
        "query": "test",
    }

    with TestClient(app) as client:
        response = client.get(f"/stream/{run_id}")
    # Response body should contain the SSE event lines
    assert "thinking" in response.text
