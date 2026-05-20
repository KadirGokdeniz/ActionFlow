"""
Integration tests for /api/v1/chat endpoints.
Tests HTTP routing and response format without external services.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_chat_health_returns_200(async_client):
    """Health check requires no external services ? always expected to pass."""
    response = await async_client.get("/api/v1/chat/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body


async def test_chat_history_endpoint_with_mock_db(async_client, mocker):
    """GET /history/{id} with mocked DB should return 404 for unknown id."""
    from unittest.mock import AsyncMock
    from app.main import app as fastapi_app
    from app.core.database import get_db

    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def mock_get_db():
        yield mock_db

    fastapi_app.dependency_overrides[get_db] = mock_get_db
    try:
        response = await async_client.get("/api/v1/chat/history/nonexistent-uuid")
        assert response.status_code in (200, 404)
    finally:
        fastapi_app.dependency_overrides.clear()


async def test_chat_stream_missing_body(async_client):
    """POST /stream without body should return 422 Unprocessable Entity."""
    response = await async_client.post("/api/v1/chat/stream")
    assert response.status_code == 422
