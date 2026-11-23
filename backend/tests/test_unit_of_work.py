"""
Unit tests for Async Unit of Work context manager
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import TransactionError
from app.core.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_unit_of_work_commit_on_success():
    mock_session = AsyncMock()
    mock_factory = MagicMock(return_value=mock_session)

    async with UnitOfWork(session_factory=mock_factory) as uow:
        assert uow.session == mock_session

    mock_session.commit.assert_awaited_once()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_rollback_on_exception():
    mock_session = AsyncMock()
    mock_session.is_active = True
    mock_factory = MagicMock(return_value=mock_session)

    with pytest.raises(ValueError, match="Test error"):
        async with UnitOfWork(session_factory=mock_factory):
            raise ValueError("Test error")

    mock_session.rollback.assert_awaited_once()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_commit_and_rollback_errors():
    uow = UnitOfWork()
    with pytest.raises(
        TransactionError, match="Cannot commit without active session context"
    ):
        await uow.commit()

    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Commit DB error")
    mock_session.is_active = True
    mock_factory = MagicMock(return_value=mock_session)

    with pytest.raises(TransactionError, match="Transaction commit failed"):
        async with UnitOfWork(session_factory=mock_factory):
            pass
