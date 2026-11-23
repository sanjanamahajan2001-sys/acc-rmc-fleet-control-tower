import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class MLEvaluationJob(BaseEntity):
    """
    SQLLogic Entity tracking automated model evaluation jobs.
    """

    __tablename__ = "ml_evaluation_jobs"

    job_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    evaluation_decision: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING_EVALUATION")

    metrics_holdout: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    threshold_rules: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    execution_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_metadata: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
