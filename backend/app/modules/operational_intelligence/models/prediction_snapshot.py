"""
WS-09 Phase 7.5 Prediction Snapshot ORM Entity

Defines PostgreSQL ORM entity mapping for `MLPredictionSnapshot` (`ml_prediction_snapshots`).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditEntity
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion


class MLPredictionSnapshot(AuditEntity):
    """
    Authoritative ML Prediction Snapshot Entity (`ml_prediction_snapshots`).
    Provides immutable prediction provenance tracing back to promoted model version, artifact SHA-256,
    FeatureSetV1 inputs, prediction cutoff timestamp, and inference outputs.
    """

    __tablename__ = "ml_prediction_snapshots"

    prediction_snapshot_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    prediction_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    prediction_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NOT_CONFIGURED", server_default=text("'NOT_CONFIGURED'"), index=True
    )

    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_model_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False, default="FeatureSetV1", server_default=text("'FeatureSetV1'"))

    dispatch_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dispatch_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    plant_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_code: Mapped[str] = mapped_column(String(50), nullable=False)

    input_features: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prediction_outputs: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    predicted_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_stale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )
    superseded_by_snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(100), ForeignKey("ml_prediction_snapshots.prediction_snapshot_id", ondelete="SET NULL"), nullable=True, index=True
    )

    lineage_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    model_version_ref: Mapped[Optional[MLModelVersion]] = relationship("MLModelVersion")

    __table_args__ = (
        Index(
            "uq_snapshot_dispatch_model_active",
            "dispatch_id",
            "model_name",
            "feature_set_version",
            unique=True,
            postgresql_where=text("is_stale = FALSE AND is_deleted = FALSE"),
        ),
    )
