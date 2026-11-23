"""
WS-10 Phase 5.1 Authoritative Prediction Error Entity (`prediction_error_records`).
Tracks prediction errors, metrics, and calibration scores across regression and classification model families.
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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class PredictionErrorRecord(BaseEntity):
    """
    Authoritative Prediction Error Record (`prediction_error_records`).
    Extensible contract supporting both Regression and Classification metrics.
    """

    __tablename__ = "prediction_error_records"

    error_record_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    outcome_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("operational_outcomes.outcome_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prediction_snapshot_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("ml_prediction_snapshots.prediction_snapshot_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False, default="FeatureSetV1")

    # Regression Contract Fields
    predicted_numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    actual_numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    absolute_error: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    squared_error: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    percentage_error: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Classification Contract Fields
    predicted_class_or_prob: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    predicted_class_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_class_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct_classification: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confusion_matrix_category: Mapped[str | None] = mapped_column(String(20), nullable=True)  # TP, TN, FP, FN
    brier_score_contribution: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Financial Exposure Error Lineage
    realized_financial_impact_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    financial_error_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Lineage & Audit Status
    is_stale_snapshot: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )
    is_superseded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )
    superseded_by_error_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_error_model_version", "model_name", "model_version"),
        Index("idx_error_snapshot_ref", "prediction_snapshot_id"),
    )
