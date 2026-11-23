"""
ERP API Module Schemas
Provides Pydantic DTOs for request/response bodies across all ERP REST endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.modules.erp.workers.tracker import ImportProgressSnapshot

T = TypeVar("T")


# =============================================================================
# 1. UPLOAD & JOB SCHEMAS
# =============================================================================


class ImportJobResponse(BaseModel):
    """
    Detailed response model for an ERP Import Job.
    """

    id: uuid.UUID
    job_number: str
    status: str
    file_name: str
    file_hash: str
    total_rows: int = 0
    processed_rows: int = 0
    error_count: int = 0
    created_at: datetime
    updated_at: datetime
    inserted_rows: int | None = None
    updated_rows: int | None = None
    uploaded_by: str | None = None
    completed_at: datetime | None = None
    is_reset: bool = False
    reset_at: datetime | None = None
    dataset_period: str | None = None
    file_type: str | None = None
    is_active_dataset: bool = False


class ChunkUploadResponse(BaseModel):
    """
    Response model for chunked workbook uploads.
    """

    session_id: str
    chunk_index: int
    received_bytes: int
    total_bytes: int
    is_complete: bool
    job: ImportJobResponse | None = None


class JobFilterParams(BaseModel):
    """
    Filter criteria for querying import jobs.
    """

    status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    plant_code: str | None = None
    customer_code: str | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = "DESC"


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated container for all API list and explorer endpoints.
    """

    items: list[T]
    total_records: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    # Backwards-compatible alias for total_records
    @property
    def total_elements(self) -> int:
        return self.total_records


class VersionedSSEEvent(BaseModel):
    """
    Versioned SSE Event payload wrapper ensuring future API client compatibility.
    """

    schema_version: str = "1.0"
    event_type: str = "erp.import.progress.v1"
    snapshot: ImportProgressSnapshot


# Expose ImportProgressSnapshot as API progress model
ProgressSnapshotResponse = ImportProgressSnapshot


class JobActionResponse(BaseModel):
    """
    Response model for async actions on import jobs (cancel, retry).
    """

    job_number: str
    action: str
    previous_status: str
    new_status: str
    message: str


# =============================================================================
# 3. STATISTICS & AUDIT LOG SCHEMAS
# =============================================================================


class ERPImportStatisticsResponse(BaseModel):
    """
    Aggregated platform import statistics and performance metrics.
    """

    total_imports: int = 0
    completed_imports: int = 0
    failed_imports: int = 0
    retried_imports: int = 0
    total_rows_imported: int = 0
    active_rows: int = 0
    active_imports: int = 0
    archived_imports: int = 0
    is_reset_active: bool = False
    average_duration_seconds: float = 0.0
    average_throughput_rows_per_sec: float = 0.0
    average_eta_seconds: float = 0.0
    average_validation_duration_seconds: float = 0.0
    average_persistence_duration_seconds: float = 0.0


class AuditLogFilterParams(BaseModel):
    """
    Filter parameters for security and operational audit logs.
    """

    job_id: uuid.UUID | None = None
    action: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class AuditLogResponse(BaseModel):
    """
    Structured representation of an import audit log entry.
    """

    id: uuid.UUID
    job_id: uuid.UUID
    action: str
    details: dict[str, Any] | None = None
    created_at: datetime


# =============================================================================
# 4. DATA EXPLORER SCHEMAS
# =============================================================================


class ExplorerQueryFilter(BaseModel):
    """
    Filter parameter DTO for Data Explorer read-only endpoints.
    """

    search: str | None = None
    plant_code: str | None = None
    customer_code: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    columns: list[str] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = "DESC"
