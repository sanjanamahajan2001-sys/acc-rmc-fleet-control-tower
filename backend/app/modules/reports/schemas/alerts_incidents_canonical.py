from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "alerts_incidents"
    report_name: str = "Alerts & Incidents Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class AlertsIncidentsKPISummary(BaseModel):
    total_active_alerts: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    acknowledged_count: int = 0

    model_config = ConfigDict(frozen=False)


class OperationalAlertRecord(BaseModel):
    alert_id: str
    alert_fingerprint: str
    alert_type: str
    severity: str
    status: str
    plant_id: str
    customer_id: str
    dispatch_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    dataset_id: str
    metric_name: str
    actual_value: float
    threshold_value: float
    unit: str
    business_impact: str
    recommended_action: str
    evidence_json: Optional[Dict[str, Any]] = None
    detected_at: str

    evaluated_at: str
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_reason: Optional[str] = None
    rule_version: str = "v1.0.0"


class CanonicalAlertsIncidentsReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: AlertsIncidentsKPISummary
    records: List[OperationalAlertRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
