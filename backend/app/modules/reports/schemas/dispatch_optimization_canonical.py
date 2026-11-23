from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "dispatch_optimization"
    report_name: str = "Dispatch Optimization Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class MetricDeltaRecord(BaseModel):
    metric_name: str
    observed_baseline: float
    optimized_value: float
    net_delta: float
    percentage_change: float
    unit: str = ""


class OptimizationKPISummary(BaseModel):
    total_dispatches: int = 0
    baseline_sla_pct: float = 0.0
    optimized_sla_pct: float = 0.0
    baseline_delay_hours: float = 0.0
    optimized_delay_hours: float = 0.0
    total_delay_hours_saved: float = 0.0
    pareto_score: float = 0.0

    model_config = ConfigDict(frozen=False)


class CandidateScenarioRecord(BaseModel):
    scenario_id: str
    scenario_name: str
    objective_type: str
    pareto_score: float
    is_recommended: bool
    constraint_violations_count: int
    sla_gain_pct: float
    delay_reduction_hrs: float


class OptimizationAssignmentRecord(BaseModel):
    dispatch_id: str
    dispatch_number: str
    vehicle_id: str
    plant_id: str
    customer_id: str
    baseline_time_out: str
    recommended_time_out: str
    time_shift_mins: float
    recommendation_reason: str


class CanonicalDispatchOptimizationReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    optimization_run_id: str = ""
    snapshot_hash: str = ""
    recommended_scenario_id: str = ""
    kpis: OptimizationKPISummary
    impact_deltas: List[MetricDeltaRecord] = []
    scenarios: List[CandidateScenarioRecord] = []
    records: List[OptimizationAssignmentRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
