"""
WS-07.2 Operational Alerts Pydantic Request & Response DTO Specifications.
Expanded in WS-07.5 and WS-07.9 for ARCHIVED status and retention contracts.
"""
from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

class AlertSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class AlertStatusEnum(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"

class OperationalDatasetContextDTO(BaseModel):
    operational_date: str = Field(..., description="ISO Operational Date (YYYY-MM-DD)")
    total_dispatches: int = Field(..., ge=0)
    last_imported_at: str = Field(..., description="ISO 8601 Last Import Timestamp")
    dataset_id: str = Field(..., description="Authoritative Dataset ID")
    status: str = Field(default="ACTIVE_PRODUCTION")

class OperationalAlertItemDTO(BaseModel):
    id: UUID
    alert_fingerprint: str = Field(..., min_length=64, max_length=64)
    alert_type: str = Field(..., min_length=1, max_length=64)
    severity: AlertSeverityEnum
    status: AlertStatusEnum
    plant_id: str
    customer_id: str
    dispatch_id: Optional[UUID] = None
    vehicle_id: Optional[str] = None
    dataset_id: str
    import_job_id: Optional[UUID] = None
    metric_name: str
    actual_value: float
    threshold_value: float
    unit: str
    business_impact: str
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: str
    detected_at: datetime
    evaluated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledgement_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_reason: Optional[str] = None
    archived_at: Optional[datetime] = None
    rule_version: str = "v1.0.0"

class AlertListResponseDTO(BaseModel):
    items: List[OperationalAlertItemDTO] = Field(..., description="Strongly typed operational alert items")
    total_count: int = Field(..., ge=0, description="Total matching alert items count before pagination")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")
    total_pages: int = Field(..., ge=1, description="Total available pages")

class AlertSummaryDTO(BaseModel):
    total_active_alerts: int = Field(..., ge=0)
    critical_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    info_count: int = Field(..., ge=0)
    acknowledged_count: int = Field(..., ge=0)
    dataset_context: OperationalDatasetContextDTO

class AlertAcknowledgeRequestDTO(BaseModel):
    acknowledged_by: str = Field(..., min_length=1, max_length=64)
    notes: Optional[str] = Field(None, max_length=500)

class AlertResolveRequestDTO(BaseModel):
    resolved_by: str = Field(..., min_length=1, max_length=255)
    resolution_reason: str = Field(..., min_length=1, max_length=255)
