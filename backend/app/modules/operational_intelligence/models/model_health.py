"""
WS-10 Phase 5.4 Authoritative Model Health Entities:
1. `ModelHealthMetric` (`model_health_metrics`)
2. `ModelHealthMetricSource` (`model_health_metric_sources`)

Tracks aggregated model family, model version, scope, and temporal health metrics,
baseline provenance, and normalized source lineage.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditEntity, BaseEntity


class ModelHealthMetric(AuditEntity):
    """
    Authoritative Model Health & Drift Metric Record (`model_health_metrics`).
    Stores global, plant, and customer aggregated performance.
    """

    __tablename__ = "model_health_metrics"

    health_record_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Model & Feature Set Identity
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_family: Mapped[str] = mapped_column(String(100), nullable=False, default="delay_regressor", index=True)
    model_version_id: Mapped[str] = mapped_column(String(100), nullable=False, default="v1.1.0-candidate-ds-fsv1-prom", index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False, default="FeatureSetV1")

    # Scope Identity
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GLOBAL", index=True)  # GLOBAL, PLANT, CUSTOMER
    scope_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # NULL for GLOBAL, plant/customer code for specific scopes

    # Temporal Boundaries
    time_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    window_type: Mapped[str] = mapped_column(String(20), nullable=False, default="30d")  # 7d, 30d, ALL_TIME
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    evaluation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Sample Denominator Breakdown
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_prediction_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regression_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    financial_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_percentage_error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    zero_actual_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Aggregated Performance Metrics
    mae: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    rmse: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    mape: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    mean_signed_error: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    median_absolute_error: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    max_absolute_error: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    precision_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    recall_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    f1_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    roc_auc: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    brier_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    psi_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)

    # Financial Exposure Aggregates
    mean_financial_error_inr: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    mae_financial_error_inr: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    total_predicted_exposure_inr: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    total_realized_impact_inr: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)

    # Governed Health State & Provenance
    health_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="INSUFFICIENT_DATA", server_default=text("'INSUFFICIENT_DATA'"), index=True
    )
    retraining_recommended: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    baseline_mae: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    baseline_f1: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    baseline_brier: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    baseline_provenance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    financial_health_policy: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Lineage & Versioning
    health_calculation_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0-phase54-health-engine")
    formula_version: Mapped[str] = mapped_column(String(50), nullable=False, default="WS54_HEALTH_STANDARD_V1")
    source_error_ids: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    is_superseded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )
    superseded_by_health_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_health_metric_aggregation_identity"),
        Index("idx_health_model_version_window", "model_version_id", "scope_type", "window_type"),
    )


class ModelHealthMetricSource(BaseEntity):
    """
    Authoritative Normalized Health Metric Lineage Record (`model_health_metric_sources`).
    Stores 100% complete link between ModelHealthMetric and prediction_error_records.
    """

    __tablename__ = "model_health_metric_sources"

    health_record_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("model_health_metrics.health_record_id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_error_record_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("prediction_error_records.error_record_id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("health_record_id", "prediction_error_record_id", name="uq_health_sources_health_error"),
        Index("idx_health_sources_error_ref", "prediction_error_record_id"),
    )
