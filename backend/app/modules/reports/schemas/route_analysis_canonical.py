import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.modules.reports.schemas.report_schemas import ReportFormat, ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "route_analysis"
    report_name: str = "Route Analysis Decision Support Report"
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    requested_by: str = "SYSTEM"


class CandidateComparisonDTO(BaseModel):
    plant_id: str
    plant_code: str
    plant_name: str
    is_current_source: bool
    is_recommended: bool
    is_viable: bool
    crow_fly_distance_km: float
    google_distance_km: Optional[float] = None
    google_duration_in_traffic_mins: Optional[float] = None
    google_static_duration_mins: Optional[float] = None
    google_traffic_delay_mins: Optional[float] = None
    historical_t1_p50_mins: Optional[float] = None
    historical_t1_p25_mins: Optional[float] = None
    historical_t1_p75_mins: Optional[float] = None
    historical_t1_iqr_mins: Optional[float] = None
    historical_sample_count: int = 0
    historical_confidence: str = "INSUFFICIENT_DATA"
    historical_winner_status: str = "NOT_EVALUATED"


class RouteAnalysisReportCanonical(BaseModel):
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any] = Field(default_factory=dict)
    effective_scope: Dict[str, Any] = Field(default_factory=dict)
    scope_fingerprint: str = ""
    status: ReportStatus = ReportStatus.COMPLETED
    record_count: int = 1

    # Analysis Identity & Scope
    analysis_id: str
    customer_id: Optional[str] = None
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    site_id: Optional[str] = None
    site_code: Optional[str] = None
    site_name: Optional[str] = None
    current_source_plant_id: Optional[str] = None
    current_source_plant_code: Optional[str] = None
    current_source_plant_name: Optional[str] = None
    recommended_plant_id: Optional[str] = None
    recommended_plant_code: Optional[str] = None
    recommended_plant_name: Optional[str] = None

    # Decision Outcome & Governance
    recommendation_status: str
    decision_case: str
    decision_template_title: str
    decision_reason_summary: str
    is_traffic_override: bool = False
    minutes_saved: Optional[float] = None
    failure_reason_code: Optional[str] = None
    analysis_mode: str = "NOW"
    planned_departure_time: Optional[str] = None
    engine_version: str = "v1.2.1"
    policy_version: str = "ROUTE_POLICY_v1.2.1"

    # Context & Lineage
    analysis_context: Optional[str] = None
    operator_notes: Optional[str] = None
    erp_import_batch_id: Optional[str] = None
    created_at: str
    created_by: Optional[str] = None

    # Google Evidence
    google_queried_at: Optional[str] = None
    google_data_freshness_seconds: int = 0
    is_google_cached: bool = False
    is_google_fresh: bool = True
    is_google_stale_cache: bool = False
    google_evidence_payload: Dict[str, Any] = Field(default_factory=dict)

    # Historical Evidence
    is_historical_sufficient: bool = False
    historical_evidence_payload: Dict[str, Any] = Field(default_factory=dict)

    # Comparison Matrix
    comparisons: List[CandidateComparisonDTO] = Field(default_factory=list)

    # Disclaimer
    disclaimer: str = (
        "Advisory Only: Truck availability is not evaluated. "
        "Final dispatch decision remains with Operations."
    )
