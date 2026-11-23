"""
Pydantic Schemas & DTOs for Telemetry Ingestion & Correlation Subsystem
Workstream X.2 Production DTOs
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ParsedTelemetryRowDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    row_number: int
    sheet_name: str
    trip_number: str | None = None
    vehicle_code: str | None = None
    plant_code: str | None = None
    site_name: str | None = None
    plant_out_timestamp: datetime | None = None
    site_arrival_timestamp: datetime | None = None
    unloading_start_timestamp: datetime | None = None
    unloading_end_timestamp: datetime | None = None
    site_departure_timestamp: datetime | None = None
    plant_return_timestamp: datetime | None = None
    max_speed_kmh: float | None = None
    avg_speed_kmh: float | None = None
    drum_rotation_rpm: float | None = None
    drum_stop_duration_mins: float | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CanonicalTelemetryDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID | None = None
    import_job_id: UUID | None = None
    dispatch_id: UUID | None = None
    vehicle_id: UUID | None = None
    trip_number: str | None = None
    plant_code: str | None = None
    site_name: str | None = None
    plant_out_timestamp: datetime | None = None
    site_arrival_timestamp: datetime | None = None
    unloading_start_timestamp: datetime | None = None
    unloading_end_timestamp: datetime | None = None
    site_departure_timestamp: datetime | None = None
    plant_return_timestamp: datetime | None = None
    max_speed_kmh: float | None = None
    avg_speed_kmh: float | None = None
    drum_rotation_rpm: float | None = None
    drum_stop_duration_mins: float | None = None
    gps_quality_score: float = 1.0
    correlation_status: str = "AWAITING_CORRELATION"
    correlation_score: float = 0.0
    source_file: str | None = None
    checksum: str | None = None
    source_lineage: dict[str, Any] | None = None


class TelemetryJobProgressDTO(BaseModel):
    job_id: str
    job_number: str
    status: str
    file_name: str
    file_hash: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    skipped_rows: int
    progress_pct: float
    worker_id: str | None = None
    error_message: str | None = None


class ManualReviewApproveRequest(BaseModel):
    review_id: UUID
    dispatch_id: UUID
    reviewer_id: str = "OPERATOR_ADMIN"
    notes: str | None = None
