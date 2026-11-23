from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field
from app.modules.reports.schemas.report_schemas import ReportFormat

class ReportDefinitionDTO(BaseModel):
    report_id: str
    name: str
    description: str
    version: str = "1.0"
    source_service: str
    supported_formats: List[ReportFormat]
    supported_filters: List[str]
    required_filters: List[str] = Field(default_factory=list)


class ReportHandlerProtocol(Protocol):
    async def generate_canonical_data(self, effective_scope: Dict[str, Any]) -> Dict[str, Any]: ...


class ReportRegistry:
    _definitions: Dict[str, ReportDefinitionDTO] = {}

    @classmethod
    def register(cls, definition: ReportDefinitionDTO): 
        if definition.report_id in cls._definitions:
            raise ValueError(f"Duplicate report id registration: {definition.report_id}")
        cls._definitions[definition.report_id] = definition

    @classmethod
    def get(cls, report_id: str) -> Optional[ReportDefinitionDTO]:
        return cls._definitions.get(report_id)

    @classmethod
    def list_all(cls) -> List[ReportDefinitionDTO]:
        return list(cls._definitions.values())

	# Register Catalog Definitions
ReportRegistry.register(ReportDefinitionDTO(
    report_id="site_operations",
    name="Site Operations Report",
    description="Detailed site operations, queue times, cycle metrics and turnaround.",
    source_service="site_dashboard",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="fleet_operations",
    name="Fleet Operations Report",
    description="Fleet-wide operational KPIs, utilization, and trip summaries.",
    source_service="operational_dashboard",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date", "shift", "dataset_type"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="site_comparison",
    name="Site Comparison Report",
    description="Cross-site comparison, efficiency ratings, and delay rankings.",
    source_service="site_comparison",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="dispatch_analysis",
    name="Dispatch Analysis Report",
    description="Detailed dispatch sequencing, turnaround, waiting, and transit execution.",
    source_service="dispatch_analysis",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date", "shift"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="dispatch_optimization",
    name="Dispatch Optimization Report",
    description="Optimization decisions, reroutering, speed limits, and bottleneck analysis.",
    source_service="dispatch_optimization",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="operational_intelligence",
    name="Operational Intelligence Report",
    description="Realized outcomes, delay/breach classifiers, and operational risk ratings.",
    source_service="operational_intelligence",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="predictive_intelligence",
    name="Predictive Intelligence Report",
    description="ML model evaluations, SLA breach predictions, feature importances, model health.",
    source_service="predictive_intelligence",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="action_execution",
    name="Control Tower Action Execution Report",
    description="Audit of planner recommendations, accepted/rejected actions, and impact logs.",
    source_service="action_execution",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))



ReportRegistry.register(ReportDefinitionDTO(
    report_id="alerts_incidents",
    name="Alerts & Incidents Report",
    description="Triggered operational alerts, breach severity, resolution status and lifecycle.",
    source_service="alerts_incidents",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))


ReportRegistry.register(ReportDefinitionDTO(
    report_id="timeline_operations",
    name="Timeline Operations Report",
    description="Chronological event logs, dispatch status changes, and vehicle state transitions.",
    source_service="timeline_operations",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))


ReportRegistry.register(ReportDefinitionDTO(
    report_id="erp_import_audit",
    name="ERP Import Audit Report",
    description="File ingestion jobs, staging logs, reconciliation statuses, and dataset hashes.",
    source_service="erp_import",
    supported_formats=[ReportFormat.XLSX, ReportFormat.JSON, ReportFormat.PDF],
    supported_filters=["operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="erp_data_explorer",
    name="ERP Data Report",
    description="Granular raw/canonical ERP records (plants, customers, dispatches, orders).",
    source_service="erp_explorer",
    supported_formats=[ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["plant_id", "customer_id", "operation_date"]
))

ReportRegistry.register(ReportDefinitionDTO(
    report_id="route_analysis",
    name="Route Analysis Decision Support Report",
    description="Deterministic 2D synthesis combining historical ERP T1 operational transit evidence with Google Routes API traffic evidence.",
    source_service="dispatch_analysis",
    supported_formats=[ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
    supported_filters=["analysis_id", "customer_id", "site_id", "plant_id"]
))
