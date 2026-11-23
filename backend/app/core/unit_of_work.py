"""
Async Unit of Work Implementation

Provides centralized async transaction management (commit, rollback, savepoints)
preventing scattered session.commit() calls across domain services.
"""

from types import TracebackType
from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.core.exceptions import TransactionError


class UnitOfWork:
    """
    Async context manager handling database session lifecycle and transaction boundaries.
    """

    def __init__(self, session_factory: Any = AsyncSessionFactory):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self.session:
            return

        try:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        """Commits current transaction session."""
        if not self.session:
            raise TransactionError("Cannot commit without active session context")
        try:
            await self.session.commit()
        except Exception as exc:
            await self.rollback()
            raise TransactionError(f"Transaction commit failed: {exc!s}") from exc

    async def rollback(self) -> None:
        """Rolls back current transaction session."""
        if self.session and self.session.is_active:
            try:
                await self.session.rollback()
            except Exception as exc:
                raise TransactionError(f"Transaction rollback failed: {exc!s}") from exc
