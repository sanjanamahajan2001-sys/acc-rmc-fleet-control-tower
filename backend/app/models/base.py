"""
Declarative Base Entity Model Hierarchy

Establishes the platform declarative metadata base, standard naming conventions,
UUID surrogate keys via pgcrypto, audit timestamps, soft-delete fields, and optimistic locking version_id.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, String, Boolean, DateTime, Integer, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Platform-wide constraint and index naming conventions dictionary
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Platform Meta Declarative Base bound to standardized naming conventions.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class BaseEntity(Base):
    """
    Base entity with surrogate UUID primary key and creation/modification timestamps.
    Standardized on pgcrypto gen_random_uuid().
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditEntity(BaseEntity):
    """
    Extends BaseEntity with creator/modifier user tracking and soft-delete capabilities.
    """

    __abstract__ = True

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class VersionedEntity(AuditEntity):
    """
    Extends AuditEntity with an optimistic concurrency locking integer version_id,
    plus production lineage metadata (is_generated, generation_reason, source_lineage).
    """

    __abstract__ = True

    version_id: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
    is_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    generation_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source_lineage: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    __mapper_args__: dict[str, Any] = {"version_id_col": version_id}  # noqa: RUF012
