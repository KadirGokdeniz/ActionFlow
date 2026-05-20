"""
Unit tests for Redis fallback behavior.
Verifies graceful degradation when Redis is unavailable.
"""
import pytest
import redis.asyncio as aioredis
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


async def test_get_state_returns_none_when_redis_unreachable(mocker):
    """get_conversation_state returns None (not raises) when Redis is down."""
    import app.core.redis as redis_module
    redis_module._redis_client = None

    mock_client = AsyncMock()
    mock_client.ping.side_effect = aioredis.ConnectionError("Redis is down")
    mocker.patch("app.core.redis.aioredis.from_url", return_value=mock_client)

    result = await redis_module.get_conversation_state("test-conv")
    assert result is None


async def test_set_state_does_not_raise_when_redis_unreachable(mocker):
    """set_conversation_state silently fails when Redis is down."""
    import app.core.redis as redis_module
    redis_module._redis_client = None

    mock_client = AsyncMock()
    mock_client.ping.side_effect = aioredis.ConnectionError("Redis is down")
    mocker.patch("app.core.redis.aioredis.from_url", return_value=mock_client)

    # Must not raise
    await redis_module.set_conversation_state("test-conv", {"key": "value"})


async def test_client_resets_on_connection_error_during_get(mocker):
    """_redis_client is reset to None when ConnectionError occurs mid-operation."""
    import app.core.redis as redis_module

    mock_client = AsyncMock()
    mock_client.get.side_effect = aioredis.ConnectionError("Lost connection")
    redis_module._redis_client = mock_client

    result = await redis_module.get_conversation_state("test-conv")

    assert result is None
    assert redis_module._redis_client is None  # Forces reconnect on next call


async def test_client_resets_on_timeout_during_set(mocker):
    """_redis_client is reset to None when TimeoutError occurs during set."""
    import app.core.redis as redis_module

    mock_client = AsyncMock()
    mock_client.set.side_effect = aioredis.TimeoutError("Timed out")
    redis_module._redis_client = mock_client

    await redis_module.set_conversation_state("test-conv", {"data": "test"})

    assert redis_module._redis_client is None


async def test_is_redis_available_returns_false_when_down(mocker):
    """is_redis_available() returns False when Redis is unreachable."""
    import app.core.redis as redis_module
    redis_module._redis_client = None

    mock_client = AsyncMock()
    mock_client.ping.side_effect = aioredis.ConnectionError("Down")
    mocker.patch("app.core.redis.aioredis.from_url", return_value=mock_client)

    result = await redis_module.is_redis_available()
    assert result is False
