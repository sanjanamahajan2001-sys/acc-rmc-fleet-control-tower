from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "site_comparison"
    report_name: str = "Site Comparison Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class SiteComparisonKPISummary(BaseModel):
    total_sites_evaluated: int = 0
    total_dispatches: int = 0
    total_volume_cum: float = 0.0
    avg_holding_mins: float = 0.0
    avg_retention_mins: float = 0.0
    avg_dispatch_accuracy: float = 0.0
    optimal_sites_count: int = 0

    model_config = ConfigDict(frozen=False)


class SiteComparisonRecord(BaseModel):
    rank: int
    site_code: str
    site_name: str
    dispatches: int
    volume_cum: float
    avg_holding_mins: float
    avg_retention_mins: float
    max_queue_tms: int
    dispatch_accuracy: float
    status: str


class CanonicalSiteComparisonReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: SiteComparisonKPISummary
    records: List[SiteComparisonRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
