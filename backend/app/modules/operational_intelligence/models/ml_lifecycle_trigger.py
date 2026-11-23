"""
WS-10.1 MLLifecycleTrigger SQLAlchemy Model.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class MLLifecycleTrigger(BaseEntity):
    """
    WS-10.1 ML Lifecycle Trigger tracking table.
    Tracks ERP import persistence completion events and their lifecycle status
    (PENDING, RUNNING, PENDING_NEXT_RUN, SKIPPED_COOLDOWN, COMPLETED, FAILED).
    """

    __tablename__ = "ml_lifecycle_triggers"

    trigger_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_family: Mapped[str] = mapped_column(
        String(100), nullable=False, default="ALL_FAMILIES", index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )
    new_dispatch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooldown_hours: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_ml_lifecycle_triggers_status_family", "status", "model_family"),
    )
