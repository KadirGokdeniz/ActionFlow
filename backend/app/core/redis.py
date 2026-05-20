import json
import logging
import os
from typing import Optional
import redis.asyncio as aioredis

logger = logging.getLogger("ActionFlow-Redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Get Redis client. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                REDIS_URL, encoding="utf-8", decode_responses=True
            )
            await _redis_client.ping()
            logger.info("Redis connection established.")
        except Exception as e:
            logger.warning(
                f"Redis unavailable: {e}. "
                "App will run without conversation state persistence."
            )
            _redis_client = None
            return None
    return _redis_client


async def close_redis():
    """Safely close Redis connection on app shutdown."""
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.aclose()
            _redis_client = None
            logger.info("Redis connection closed.")
        except Exception as e:
            logger.warning(f"Redis close error: {e}")


async def set_conversation_state(
    conversation_id: str, state: dict, ttl: int = 86400
):
    """Save conversation state to Redis. Silently degrades if Redis is down."""
    global _redis_client
    client = await get_redis()
    if not client:
        return
    try:
        await client.set(f"conv_state:{conversation_id}", json.dumps(state), ex=ttl)
    except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.warning(f"Redis connection lost during set: {e}. Will reconnect.")
        _redis_client = None  # Force reconnect on next call
    except Exception as e:
        logger.error(f"Redis set error: {e}")


async def get_conversation_state(conversation_id: str) -> Optional[dict]:
    """Get conversation state from Redis. Returns None if Redis is down."""
    global _redis_client
    client = await get_redis()
    if not client:
        return None
    try:
        data = await client.get(f"conv_state:{conversation_id}")
        if data:
            return json.loads(data)
    except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.warning(f"Redis connection lost during get: {e}. Will reconnect.")
        _redis_client = None
    except Exception as e:
        logger.error(f"Redis get error: {e}")
    return None


async def delete_conversation_state(conversation_id: str):
    """Delete conversation state from Redis. Silently degrades if Redis is down."""
    global _redis_client
    client = await get_redis()
    if not client:
        return
    try:
        await client.delete(f"conv_state:{conversation_id}")
    except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.warning(f"Redis connection lost during delete: {e}. Will reconnect.")
        _redis_client = None
    except Exception as e:
        logger.error(f"Redis delete error: {e}")


async def is_redis_available() -> bool:
    """Health check for Redis. Returns False if unavailable."""
    try:
        client = await get_redis()
        if client:
            await client.ping()
            return True
    except Exception:
        pass
    return False
