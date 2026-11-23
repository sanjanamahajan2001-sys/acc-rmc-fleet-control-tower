"""
WS-10.2 ML Dataset Entity definition.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class MLDataset(BaseEntity):
    """
    SQLAlchemy Entity representing persisted FeatureSetV1 training dataset lineage and metadata.
    """

    __tablename__ = "ml_datasets"

    dataset_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    feature_set_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="FeatureSetV1", index=True
    )
    trigger_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_erp_job_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    train_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    val_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    holdout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_date_min: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    operation_date_max: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    lineage_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    exclusion_stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    target_availability: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

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
