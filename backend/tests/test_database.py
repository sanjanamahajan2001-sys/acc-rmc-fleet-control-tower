"""
Unit and Integration Tests for Database Infrastructure
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.database import check_database_health, engine, get_db_session


@pytest.mark.asyncio
async def test_database_engine_pool_configuration():
    assert engine.pool.size() == 20
    assert engine.pool._max_overflow == 10


@pytest.mark.asyncio
async def test_get_db_session_dependency():
    mock_session = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_cm)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.database.AsyncSessionFactory", mock_factory)
        gen = get_db_session()
        session = await gen.__anext__()
        assert session == mock_session
        await gen.aclose()


@pytest.mark.asyncio
async def test_check_database_health_mock():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_session.execute.return_value = mock_result

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock(return_value=mock_cm)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.database.AsyncSessionFactory", mock_factory)
        health = await check_database_health()
        assert health["status"] == "healthy"
        assert health["pool_size"] == 20
