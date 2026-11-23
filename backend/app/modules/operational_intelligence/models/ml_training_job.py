"""
WS-10.3 ML Training Job Entity definition.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class MLTrainingJob(BaseEntity):
    """
    SQLAlchemy Entity tracking training execution jobs, statuses, artifact metadata, and error details.
    """

    __tablename__ = "ml_training_jobs"

    job_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    trigger_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    dataset_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    model_family: Mapped[str] = mapped_column(
        String(100), nullable=False, default="ALL_FAMILIES"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )

    models_trained_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trained_model_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    execution_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
