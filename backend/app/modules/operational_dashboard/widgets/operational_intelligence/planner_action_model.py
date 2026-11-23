"""
Phase 5.7 Planner Action Data Model.
PostgreSQL table definition for storing immutable planner action audit records.
"""

from sqlalchemy import Column, String, DateTime, JSON, Text
from datetime import datetime, timezone
from app.models.base import Base


class PlannerActionAuditRecord(Base):
    """Authoritative Phase 5.7 Planner Action Audit DB Table."""

    __tablename__ = "planner_action_audit_records"

    action_id = Column(String, primary_key=True, index=True)
    optimization_run_id = Column(String, nullable=False, index=True)
    scenario_id = Column(String, nullable=False, index=True)
    objective_type = Column(String, nullable=False)
    snapshot_hash = Column(String, nullable=False, index=True)
    action_type = Column(String, nullable=False)
    modified_parameters = Column(JSON, nullable=True)
    rejection_reason = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
