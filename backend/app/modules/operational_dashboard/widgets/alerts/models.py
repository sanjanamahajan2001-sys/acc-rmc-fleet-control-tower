"""
WS-07.2 Operational Alerts SQLAlchemy Model Definition.
Updated in WS-07.9 for archived_at timestamp tracking.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base

class OperationalAlertModel(Base):
    """
    SQLAlchemy Model representing the persisted operational_alerts table.
    """
    __tablename__ = "operational_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_fingerprint = Column(String(64), nullable=False)
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False) # 'CRITICAL', 'WARNING', 'INFO'
    status = Column(String(16), nullable=False, default="OPEN") # 'OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'ARCHIVED'

    # Entity & Scope Identifiers
    plant_id = Column(String(64), nullable=False)
    customer_id = Column(String(64), nullable=False)
    dispatch_id = Column(UUID(as_uuid=True), nullable=True)
    vehicle_id = Column(String(32), nullable=True)
    dataset_id = Column(String(64), nullable=False)
    import_job_id = Column(UUID(as_uuid=True), nullable=True)

    # Metric Evidence & Provenance
    metric_name = Column(String(64), nullable=False)
    actual_value = Column(Numeric(10, 2), nullable=False)
    threshold_value = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(16), nullable=False)
    business_impact = Column(String(255), nullable=False)
    evidence_json = Column(JSONB, nullable=False, default=dict)
    recommended_action = Column(String(255), nullable=False)

    # Lifecycle Audit Timestamps
    detected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(64), nullable=True)
    acknowledgement_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(64), nullable=True)
    resolution_reason = Column(String(255), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    rule_version = Column(String(32), nullable=False, default="v1.0.0")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("alert_fingerprint", "dataset_id", name="uq_alerts_fingerprint_dataset"),
        Index("idx_alerts_scope", "plant_id", "customer_id", "status"),
    )
