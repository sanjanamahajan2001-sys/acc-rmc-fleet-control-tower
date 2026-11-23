from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "site_operations"
    report_name: str = "Site Operations Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class SiteOperationsKPIs(BaseModel):
    total_dispatches: int = 0
    within_sla_count: int = 0
    outside_sla_count: int = 0
    compliance_pct: float = 0.0
    violation_pct: float = 0.0
    avg_holding_mins: float = 0.0
    percentile_95_holding_mins: float = 0.0
    max_holding_mins: float = 0.0
    avg_retention_mins: float = 0.0
    max_retention_mins: float = 0.0
    avg_site_time_mins: float = 0.0

    model_config = ConfigDict(frozen=False)


class DelayDistributionRecord(BaseModel):
    severity: str
    count: int
    percentage: float


class SiteInsightRecord(BaseModel):
    category: str
    title: str
    impact_level: str
    insight_text: str


class CanonicalSiteOperationsReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: SiteOperationsKPIs
    delay_distribution: List[DelayDistributionRecord] = []
    insights: List[SiteInsightRecord] = []
    records: List[Any] = []

    model_config = ConfigDict(frozen=False)

