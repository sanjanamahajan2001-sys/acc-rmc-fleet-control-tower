"""
WS-ROUT-4: Route Analysis Snapshot Model
Authoritative ORM mapping for route_analysis_snapshots.
"""

import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import VersionedEntity


class RouteAnalysisSnapshot(VersionedEntity):
    """
    Authoritative, Immutable Audit Record of a Route Analysis Query.
    Guarantees 100% historical reproducibility of every operational recommendation and failure state.
    """
    __tablename__ = "route_analysis_snapshots"

    # 1. Identity & Scope (Nullable where failed before scope resolution)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    current_source_plant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    recommended_plant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)

    # 2. Decision Outcome & State Machine
    recommendation_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    failure_reason_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    analysis_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="NOW")  # NOW | PLANNED_DEPARTURE
    planned_departure_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.2.1")
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False, default="ROUTE_POLICY_v1.2.1")
    decision_reason_summary: Mapped[str] = mapped_column(Text, nullable=False)

    # 3. Audit Context & Lineage
    analysis_context: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    erp_import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # 4. Immutable Structured Evidence Payloads
    historical_evidence_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    google_evidence_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    candidate_comparison_matrix: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    # 5. Freshness & Provider Lineage
    google_queried_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data_freshness_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_cached_result: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    queried_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_route_snapshots_site_date", "site_id", "queried_at"),
        Index("idx_route_snapshots_status", "recommendation_status"),
    )
