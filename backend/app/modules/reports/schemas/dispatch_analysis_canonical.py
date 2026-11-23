from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.modules.reports.schemas.report_schemas import ReportFormat, ReportStatus

class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "dispatch_analysis"
    report_name: str = "Dispatch Analysis Report"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    requested_by: str = "system"


class DispatchAnalysisRecord(BaseModel):
    dispatch_id: str
    dispatch_number: str
    dispatch_date: str
    time_out: Optional[str] = None
    time_in: Optional[str] = None
    plant_code: str
    customer_code: str
    customer_name: str
    vehicle_id: str
    driver_name: str
    interval_mins: float
    variance_mins: float
    holding_mins: float
    retention_mins: float
    sla_status: str
    trip_status: str
    cadence_recommendation: str


class DispatchAnalysisKPIs(BaseModel):
    total_dispatches: int = 0
    on_schedule_dispatches: int = 0
    sla_compliance_pct: float = 0.0
    avg_interval_mins: float = 0.0
    interval_variance_mins: float = 0.0
    das_score_pct: float = 0.0
    completed_dispatches: int = 0
    avg_loading_mins: float = 0.0
    avg_transit_mins: float = 0.0
    recommended_interval_mins: float = 15.0
    cadence_status: str = "OPTIMAL"
    potential_delay_reduction_hrs: float = 0.0


class DelayCategoryBreakdown(BaseModel):
    category_name: str
    delay_hours: float
    percentage_contribution: float
    affected_trips_count: int
    severity: str
    recommendation: str


class CanonicalDispatchAnalysisReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: DispatchAnalysisKPIs
    records: List[DispatchAnalysisRecord] = Field(default_factory=list)
    delay_categories: List[DelayCategoryBreakdown] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
