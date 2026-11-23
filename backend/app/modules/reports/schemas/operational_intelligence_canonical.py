from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "operational_intelligence"
    report_name: str = "Operational Intelligence Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class OperationalIntelligenceKPISummary(BaseModel):
    total_sites_evaluated: int = 0
    total_trips: int = 0
    avg_sri_score: float = 0.0
    avg_swi_site: float = 0.0
    avg_dpi_site: float = 0.0
    avg_fui_site: float = 0.0
    grade_a_sites_count: int = 0

    model_config = ConfigDict(frozen=False)


class SiteReadinessRecord(BaseModel):
    rank: int
    site_id: str
    site_name: str
    total_trips: int
    swi_site: float
    dpi_site: float
    fui_site: float
    sri_score: float
    grade: str


class CanonicalOperationalIntelligenceReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: OperationalIntelligenceKPISummary
    health: Dict[str, Any] = {}
    alerts: Dict[str, Any] = {}
    recommendations: Dict[str, Any] = {}
    financial_exposure: Dict[str, Any] = {}
    efficiency: Dict[str, Any] = {}
    cost_exposure: Dict[str, Any] = {}
    records: List[SiteReadinessRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)

