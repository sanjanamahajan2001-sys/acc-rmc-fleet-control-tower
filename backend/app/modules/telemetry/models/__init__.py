"""
SQLAlchemy Models for Telemetry Ingestion & Correlation Subsystem
Workstream X.2 Production Models
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    FLOAT,
    INTEGER,
    TEXT,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseEntity


class UploadedWorkbook(BaseEntity):
    __tablename__ = "uploaded_workbooks"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: str = Column(VARCHAR(255), nullable=False)
    file_path: str = Column(VARCHAR(500), nullable=False)
    file_size_bytes: int = Column(BIGINT, nullable=False)
    mime_type: str = Column(VARCHAR(100), nullable=False)
    checksum: str = Column(VARCHAR(64), nullable=False, unique=True)
    source_type: str = Column(VARCHAR(50), nullable=False)
    status: str = Column(VARCHAR(50), nullable=False, default="REGISTERED")
    uploaded_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class FleetTelemetryMetric(BaseEntity):
    __tablename__ = "fleet_telemetry_metrics"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_job_id: Any = Column(UUID(as_uuid=True), ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True)
    dispatch_id: Any = Column(UUID(as_uuid=True), ForeignKey("dispatches.id", ondelete="SET NULL"), nullable=True)
    vehicle_id: Any = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=True)
    
    trip_number: str | None = Column(VARCHAR(100), nullable=True)
    plant_code: str | None = Column(VARCHAR(50), nullable=True)
    site_name: str | None = Column(VARCHAR(255), nullable=True)
    
    plant_out_timestamp: datetime | None = Column(DateTime(timezone=True), nullable=True)
    site_arrival_timestamp: datetime | None = Column(DateTime(timezone=True), nullable=True)
    unloading_start_timestamp: datetime | None = Column(DateTime(timezone=True), nullable=True)
    unloading_end_timestamp: datetime | None = Column(DateTime(timezone=True), nullable=True)
    site_departure_timestamp: datetime | None = Column(DateTime(timezone=True), nullable=True)
    plant_return_timestamp: datetime | None = Column(DateTime(timezone=True), nullable=True)
    
    max_speed_kmh: float | None = Column(FLOAT, nullable=True)
    avg_speed_kmh: float | None = Column(FLOAT, nullable=True)
    drum_rotation_rpm: float | None = Column(FLOAT, nullable=True)
    drum_stop_duration_mins: float | None = Column(FLOAT, nullable=True)
    gps_quality_score: float = Column(FLOAT, default=1.0)
    
    correlation_status: str = Column(VARCHAR(50), default="AWAITING_CORRELATION")
    correlation_score: float = Column(FLOAT, default=0.0)
    source_file: str | None = Column(VARCHAR(255), nullable=True)
    checksum: str | None = Column(VARCHAR(64), nullable=True)
    source_lineage: dict[str, Any] | None = Column(JSONB, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class FailedTelemetryRow(BaseEntity):
    __tablename__ = "tbl_failed_telemetry_rows"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_job_id: Any = Column(UUID(as_uuid=True), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False)
    row_number: int = Column(INTEGER, nullable=False)
    raw_payload: dict[str, Any] = Column(JSONB, nullable=False)
    error_code: str = Column(VARCHAR(100), nullable=False)
    error_message: str = Column(TEXT, nullable=False)
    retry_supported: bool = Column(BOOLEAN, default=True)
    quarantined_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class CorrelationRule(BaseEntity):
    __tablename__ = "tbl_correlation_rules"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name: str = Column(VARCHAR(100), nullable=False, unique=True)
    weight: float = Column(FLOAT, nullable=False)
    priority: int = Column(INTEGER, nullable=False)
    enabled: bool = Column(BOOLEAN, default=True)
    threshold: float = Column(FLOAT, default=0.70)
    description: str | None = Column(TEXT, nullable=True)


class CorrelationHistory(BaseEntity):
    __tablename__ = "tbl_correlation_history"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_id: Any = Column(UUID(as_uuid=True), ForeignKey("dispatches.id", ondelete="RESTRICT"), nullable=True)
    telemetry_id: Any = Column(UUID(as_uuid=True), ForeignKey("fleet_telemetry_metrics.id", ondelete="CASCADE"), nullable=False)
    rules_applied: dict[str, Any] = Column(JSONB, nullable=False)
    confidence_score: float = Column(FLOAT, nullable=False)
    matched_by: str = Column(VARCHAR(100), nullable=False)
    correlation_engine_version: str = Column(VARCHAR(50), nullable=False, default="v2.0.0")
    rule_set_version: str = Column(VARCHAR(50), nullable=False, default="v1.4.0")
    parser_version: str = Column(VARCHAR(50), nullable=False, default="v3.1.0")
    execution_timestamp: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ManualReviewItem(BaseEntity):
    __tablename__ = "manual_review_queue"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telemetry_id: Any = Column(UUID(as_uuid=True), ForeignKey("fleet_telemetry_metrics.id", ondelete="CASCADE"), nullable=False)
    candidate_dispatches: dict[str, Any] = Column(JSONB, nullable=False)
    highest_score: float = Column(FLOAT, nullable=False)
    review_status: str = Column(VARCHAR(50), default="PENDING_REVIEW")
    is_manual_override: bool = Column(BOOLEAN, default=False)
    reviewer_id: str | None = Column(VARCHAR(100), nullable=True)
    reviewer_notes: str | None = Column(TEXT, nullable=True)
    reviewed_at: datetime | None = Column(DateTime(timezone=True), nullable=True)
