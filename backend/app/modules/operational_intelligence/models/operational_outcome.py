"""
WS-10 Phase 5.1 Authoritative Operational Outcome Entity (`operational_outcomes`).
Stores verified real-world ERP outcomes for dispatches (transit duration, unloading duration, SLA breach flag, plant risk class).
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


class OperationalOutcome(BaseEntity):
    """
    Authoritative Operational Outcome Record (`operational_outcomes`).
    Tracks canonical ERP actuals matched to dispatches.
    """

    __tablename__ = "operational_outcomes"

    outcome_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    dispatch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dispatches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dispatch_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prediction_snapshot_id: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("ml_prediction_snapshots.prediction_snapshot_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Actual ERP Outcomes
    actual_transit_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_unloading_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_sla_breach_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_plant_risk_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_financial_impact_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Outcome Verification Lifecycle: RECEIVED -> VALIDATED -> VERIFIED
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RECEIVED", server_default=text("'RECEIVED'"), index=True
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )

    # Immutable Correction & Supersession Lineage
    is_superseded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), index=True
    )
    superseded_by_outcome_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps & Provenance
    outcome_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source_event_type: Mapped[str] = mapped_column(String(100), nullable=False, default="ERP_DISPATCH_COMPLETED")
    audit_metadata: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_outcomes_dispatch_ver", "dispatch_id", "verification_status"),
        Index("idx_outcomes_snapshot_ref", "prediction_snapshot_id"),
    )
