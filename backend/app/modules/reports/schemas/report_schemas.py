from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ReportFormat(str, Enum):
    PDF = "PDF"
    XLSX = "XLSX"
    JSON = "JSON"


class ReportStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SCOPE_VALIDATION_FAILED = "SCOPE_VALIDATION_FAILED"
    NO_DATA = "NO_DATA"
    PURGED = "PURGED"




class ScopeValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    INVALID_SCOPE = "INVALID_SCOPE"
    PARTIAL = "PARTIAL"


class ReportScopeDTO(BaseModel):
    plant_id: str = Field(default="ALL", description="Plant Code or ALL")
    customer_id: str = Field(default="ALL", description="Customer Code or ALL")
    operation_date: str = Field(default="2026-08-05", description="Operational date YYYY-MM-DD")
    shift: str = Field(default="ALL", description="Shift name or ALL")
    dataset_type: str = Field(default="ALL", description="Dataset type (ALL, REAL_ONLY, SYNTHETIC_ONLY)")

    @field_validator("plant_id", "customer_id", "shift", "dataset_type", mode="before")
    @classmethod
    def normalize_string(cls, v: Any) -> str:
        if not v or not str(v).strip():
            return "ALL"
        return str(v).strip().upper()

    @field_validator("operation_date", mode="before")
    @classmethod
    def validate_operation_date(cls, v: Any) -> str:
        if not v or not str(v).strip():
            return "2026-08-05"
        val = str(v).strip()
        parts = val.split("-")
        if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            raise ValueError("operation_date must be in YYYY-MM-DD format")
        return val


class AuthoritativeScopeDTO(ReportScopeDTO):
    resolved_dataset_id: str = Field(default="DS-20260805-001")
    import_job_id: Optional[str] = None
    calculation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scope_fingerprint: str = ""
    record_count: int = 0


class ReportRequestDTO(BaseModel):
    report_id: str = Field(..., description="Unique report identifier")
    format: ReportFormat = Field(default=ReportFormat.PDF)
    scope: ReportScopeDTO = Field(default_factory=ReportScopeDTO)
    requested_by: str = Field(default="SYSTEM")


class ReportExecutionResponse(BaseModel):
    execution_id: str
    report_id: str
    report_type: str
    format: ReportFormat
    requested_by: str
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    scope_validation_status: ScopeValidationStatus
    record_count: int = 0
    dataset_id: Optional[str] = None
    status: ReportStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    artifact_path: Optional[str] = None
    file_size_bytes: Optional[int] = None

