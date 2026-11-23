"""
Generic Async Repository Base Implementation

Provides standardized async persistence operations (CRUD, soft-delete, pagination,
streaming, bulk ops) for SQLAlchemy models without domain logic bloat.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecordNotFoundError
from app.models.base import AuditEntity, BaseEntity
from app.repositories.pagination import Page, PageRequest
from app.repositories.specification import Specification

T = TypeVar("T", bound=BaseEntity)


class GenericRepository(Generic[T]):
    """
    Generic Async Repository encapsulating persistence access for entity type T.
    MUST NOT contain business rules, calculations, validation, or authorization logic.
    """

    def __init__(self, model_cls: type[T], session: AsyncSession):
        self.model_cls = model_cls
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> T:
        """
        Fetch entity by UUID primary key.
        Raises RecordNotFoundError if record doesn't exist or is soft-deleted.
        """
        stmt = select(self.model_cls).where(self.model_cls.id == id)
        if issubclass(self.model_cls, AuditEntity):
            stmt = stmt.where(self.model_cls.is_deleted == False)

        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        if not entity:
            raise RecordNotFoundError(
                f"{self.model_cls.__name__} with ID {id} not found",
                details={"entity_type": self.model_cls.__name__, "id": str(id)},
            )
        return entity

    async def find(
        self,
        spec: Specification[T] | None = None,
        page_request: PageRequest | None = None,
    ) -> Page[T]:
        """
        Fetch paginated records matching optional Specification filter.
        """
        page_req = page_request or PageRequest()

        # Base query filtering soft-deleted records
        stmt = select(self.model_cls)
        count_stmt = select(func.count()).select_from(self.model_cls)

        if issubclass(self.model_cls, AuditEntity):
            stmt = stmt.where(self.model_cls.is_deleted == False)
            count_stmt = count_stmt.where(self.model_cls.is_deleted == False)

        if spec:
            expr = spec.to_expression()
            stmt = stmt.where(expr)
            count_stmt = count_stmt.where(expr)

        # Count total matching records
        total_result = await self.session.execute(count_stmt)
        total_elements = total_result.scalar_one() or 0

        # Sorting & Pagination
        if page_req.sort_by and hasattr(self.model_cls, page_req.sort_by):
            col = getattr(self.model_cls, page_req.sort_by)
            stmt = stmt.order_by(
                col.desc() if page_req.sort_order == "DESC" else col.asc()
            )
        else:
            stmt = stmt.order_by(self.model_cls.created_at.desc())

        stmt = stmt.offset(page_req.offset).limit(page_req.size)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return Page.create(
            items=items, total_elements=total_elements, page_request=page_req
        )

    async def create(self, entity: T) -> T:
        """Persists a new entity instance to database session."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_many(self, entities: Sequence[T]) -> Sequence[T]:
        """Bulk adds multiple entity instances to database session."""
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def update(self, entity: T) -> T:
        """Flushes entity changes to database session."""
        await self.session.flush()
        return entity

    async def soft_delete(
        self, id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> None:
        """
        Soft deletes entity by setting is_deleted=True and deleted_at timestamp.
        """
        entity = await self.get_by_id(id)
        if isinstance(entity, AuditEntity):
            entity.is_deleted = True
            entity.deleted_at = datetime.now(timezone.utc)
            if user_id:
                entity.updated_by = user_id
            await self.session.flush()

    async def hard_delete(self, id: uuid.UUID) -> None:
        """Permanently removes entity from database table."""
        entity = await self.get_by_id(id)
        await self.session.delete(entity)
        await self.session.flush()
