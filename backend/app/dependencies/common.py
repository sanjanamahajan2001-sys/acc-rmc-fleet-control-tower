"""
Shared FastAPI Dependency Injection Package

Provides reusable dependencies for FastAPI routes (database sessions, UnitOfWork,
RequestContext state) ensuring consistent resource management.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.database import AsyncSessionFactory
from app.core.unit_of_work import UnitOfWork


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per HTTP request.
    Automatically rolls back on uncaught exception and closes session on completion.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """
    FastAPI dependency yielding a UnitOfWork instance per HTTP request.
    Enforces transaction commit on success and rollback on exception.
    """
    async with UnitOfWork() as uow:
        yield uow


def get_current_request_context() -> type[RequestContext]:
    """
    FastAPI dependency injecting the thread/async-safe RequestContext accessor.
    """
    return RequestContext
