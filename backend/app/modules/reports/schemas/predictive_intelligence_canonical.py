from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "predictive_intelligence"
    report_name: str = "Predictive Intelligence Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class PredictiveKPISummary(BaseModel):
    promoted_model_count: int = 0
    total_snapshots_found: int = 0
    avg_predicted_delay_mins: float = 0.0
    avg_confidence_score: float = 0.0
    total_financial_risk_inr: float = 0.0

    model_config = ConfigDict(frozen=False)


class PredictionSnapshotRecord(BaseModel):
    prediction_snapshot_id: str
    prediction_timestamp: str
    prediction_status: str
    model_name: str
    model_version: str
    feature_set_version: str
    dispatch_id: Optional[str] = None
    dispatch_code: Optional[str] = None
    plant_code: Optional[str] = None
    customer_code: Optional[str] = None
    vehicle_code: Optional[str] = None
    target_name: str
    predicted_value: Optional[float] = None
    confidence_score: Optional[float] = None
    financial_exposure_inr: Optional[float] = None
    total_financial_risk_inr: Optional[float] = None


class CanonicalPredictiveIntelligenceReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    overall_authority_status: str = "NOT_CONFIGURED"
    kpis: PredictiveKPISummary
    records: List[PredictionSnapshotRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
