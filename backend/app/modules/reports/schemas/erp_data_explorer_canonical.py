from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "erp_data_explorer"
    report_name: str = "ERP Data Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class ERPDataExplorerKPISummary(BaseModel):
    total_plants: int = 0
    total_customers: int = 0
    total_dispatches: int = 0
    correlated_dispatches_count: int = 0

    model_config = ConfigDict(frozen=False)


class ERPDispatchRecord(BaseModel):
    dispatch_id: str
    dispatch_number: str
    plant_name: Optional[str] = None
    customer_name: Optional[str] = None
    vehicle_code: Optional[str] = None
    status: str
    telemetry_status: str
    correlation_score: Optional[str] = None
    time_out: Optional[str] = None
    time_in: Optional[str] = None
    cycle_time: Optional[float] = None


class CanonicalERPDataExplorerReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: ERPDataExplorerKPISummary
    records: List[ERPDispatchRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
