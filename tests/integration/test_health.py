"""Integration tests for health check endpoints."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_liveness_returns_200(async_client):
    """/health/live always returns 200."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


async def test_readiness_returns_503_when_db_down(async_client, mocker):
    """/health/ready returns 503 when DB is unavailable."""
    mocker.patch(
        "app.core.database.get_async_engine",
        side_effect=Exception("DB connection failed")
    )
    mocker.patch("app.core.redis.is_redis_available", return_value=False)

    response = await async_client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert "database" in response.json()["checks"]


async def test_readiness_redis_unavailable_still_ready(async_client, mocker):
    """Redis down should not block readiness (non-critical)."""
    from unittest.mock import AsyncMock, MagicMock
    from sqlalchemy.ext.asyncio import AsyncConnection

    mock_conn = AsyncMock(spec=AsyncConnection)
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_conn)
    mocker.patch("app.core.database.get_async_engine", return_value=mock_engine)
    mocker.patch("app.core.redis.is_redis_available", return_value=False)

    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "non-critical" in response.json()["checks"]["redis"]
