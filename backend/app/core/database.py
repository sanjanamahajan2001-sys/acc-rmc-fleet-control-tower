"""
Async Database Infrastructure Package

Configures SQLAlchemy 2.x async engine, async session factory, connection pooling,
and FastAPI database session dependency injection.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.exceptions import DatabaseConnectionError

# Production-grade Async SQLAlchemy Engine configuration
engine: AsyncEngine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30.0,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
)

# Async Session Factory
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session.
    Automatically handles cleanup on request completion.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> dict[str, Any]:
    """
    Executes a health check ping (SELECT 1) against PostgreSQL.
    Returns database readiness status and pool metrics.
    """
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            if value != 1:
                raise DatabaseConnectionError(
                    "Database ping returned unexpected response"
                )

        pool = engine.pool
        size = getattr(pool, "size", lambda: 20)()
        checkedin = getattr(pool, "checkedin", lambda: 0)()
        checkedout = getattr(pool, "checkedout", lambda: 0)()
        overflow = getattr(pool, "overflow", lambda: 0)()

        return {
            "status": "healthy",
            "pool_size": size,
            "checked_in": checkedin,
            "checked_out": checkedout,
            "overflow": overflow,
        }
    except Exception as exc:
        raise DatabaseConnectionError(f"Database health check failed: {exc!s}") from exc
