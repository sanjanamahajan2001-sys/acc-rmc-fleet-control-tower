"""
Unit tests for Redis Async Connection Manager
"""

import pytest

from app.core.redis import check_redis_health, close_redis, get_redis_client


@pytest.mark.asyncio
async def test_redis_client_acquisition():
    client = get_redis_client()
    assert client is not None


@pytest.mark.asyncio
async def test_redis_health_probe():
    health = await check_redis_health()
    assert "status" in health
    await close_redis()
