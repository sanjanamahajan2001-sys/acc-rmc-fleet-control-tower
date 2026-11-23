from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "action_execution"
    report_name: str = "Control Tower Action Execution Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class ActionExecutionKPISummary(BaseModel):
    total_actions: int = 0
    pending_count: int = 0
    accepted_count: int = 0
    in_progress_count: int = 0
    executed_count: int = 0
    deferred_count: int = 0
    rejected_count: int = 0
    total_avoided_exposure_inr: float = 0.0

    model_config = ConfigDict(frozen=False)



class ActionLogRecord(BaseModel):
    action_id: str
    recommendation_id: str
    prediction_snapshot_id: Optional[str] = None
    model_family: Optional[str] = None
    model_version: Optional[str] = None
    dataset_id: Optional[str] = None
    plant_code: str
    customer_code: Optional[str] = None
    dispatch_id: Optional[str] = None
    dispatch_code: Optional[str] = None
    action_type: str
    action_status: str
    dispatcher_id: str
    dispatcher_role: str
    predicted_risk_exposure_inr: Optional[float] = None
    estimated_avoided_exposure_inr: Optional[float] = None
    actual_avoided_loss_inr: Optional[float] = None
    decision_timestamp: Optional[str] = None
    execution_confirmed_at: Optional[str] = None
    reason_code: Optional[str] = None
    dispatcher_notes: Optional[str] = None
    trigger_explanation: Optional[str] = None
    action_parameters: Optional[Dict[str, Any]] = None



class CanonicalActionExecutionReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: ActionExecutionKPISummary
    records: List[ActionLogRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
