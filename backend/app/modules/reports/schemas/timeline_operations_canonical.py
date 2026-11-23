from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "timeline_operations"
    report_name: str = "Timeline Operations Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class TimelineOperationsKPISummary(BaseModel):
    total_dispatches: int = 0
    total_timeline_events: int = 0
    dispatches_with_telemetry: int = 0
    complete_duration_count: int = 0

    model_config = ConfigDict(frozen=False)


class TimelineEventRecord(BaseModel):
    event_id: str
    event_type: str
    authority_type: str
    timestamp: Optional[str] = None
    duration_mins: Optional[float] = None
    location_name: Optional[str] = None
    is_inferred_estimate: bool = False
    notes: Optional[str] = None
    dispatch_id: str
    dispatch_number: str
    plant_id: str
    customer_id: str
    vehicle_id: Optional[str] = None
    status: str


class CanonicalTimelineOperationsReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: TimelineOperationsKPISummary
    records: List[TimelineEventRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
