"""
Redis Async Connection Manager & Pool

Provides async Redis connection pool management, health check probes,
and graceful connection cleanup.
"""

from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.redis")

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """
    Returns an async Redis client bound to current event loop.
    """
    global _redis_client
    if _redis_client is None:
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        _redis_client = aioredis.from_url(
            redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return _redis_client


async def check_redis_health() -> dict[str, Any]:
    """
    Pings Redis server and returns operational health status.
    """
    try:
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(redis_url, decode_responses=True)
        pong = await client.ping()
        await client.aclose()
        if pong:
            return {"status": "healthy", "mode": "standalone"}
        return {"status": "unhealthy", "reason": "Ping failed"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis health check failed", error=str(exc))
        return {"status": "unhealthy", "reason": str(exc)}


async def close_redis() -> None:
    """
    Disposes Redis client cleanly.
    """
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
    logger.info("Redis client closed cleanly")
