"""
Phase 8 — Workstream 1: Authoritative Planner Action Execution Extension Entity.
Extends Phase 5.7 Planner Action Audit DB model to store dispatcher decision/execution lineage,
prediction snapshot references, model version provenance, optimistic concurrency locks, and idempotency keys.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from sqlalchemy import String, DateTime, Text, Float, Integer, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlannerActionLog(Base):
    """
    Authoritative Phase 8 / Phase 5.7 Planner Action Log (`tbl_planner_action_log`).
    Tracks immutable planner & dispatcher action decisions, execution status transitions,
    prediction snapshot lineage, financial risk exposure attribution, and outcome matching references.
    """

    __tablename__ = "tbl_planner_action_log"

    action_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prediction_snapshot_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    model_family: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operation_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    plant_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    dispatch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    dispatch_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    predicted_risk_exposure_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_avoided_exposure_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_avoided_loss_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    action_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", server_default=text("'PENDING'"), index=True
    )

    dispatcher_id: Mapped[str] = mapped_column(String(100), nullable=False, default="SYSTEM", server_default=text("'SYSTEM'"))
    dispatcher_role: Mapped[str] = mapped_column(String(50), nullable=False, default="DISPATCHER", server_default=text("'DISPATCHER'"))
    
    decision_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deferred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reason_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dispatcher_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    version_lock: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=text("now()")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
