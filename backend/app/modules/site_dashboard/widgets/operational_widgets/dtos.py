"""
Operational Widgets DTO Specifications
Workstream 2.10 Backend DTOs
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class DashboardHealthDTO(BaseModel):
    dashboard_status: Literal["GOOD", "WARNING", "CRITICAL"]
    last_erp_import: str
    backend_processing_time_ms: float
    calculation_duration_ms: float
    canonical_snapshot_version: str
    total_records_evaluated: int
    import_completeness_pct: float
    database_freshness: str
    canonical_sync_status: Literal["SYNCHRONIZED", "LAGGING", "OUT_OF_SYNC"]

    model_config = ConfigDict(frozen=True)


class SystemReadinessItemDTO(BaseModel):
    component: str
    status: Literal["GOOD", "WARNING", "CRITICAL"]
    detail_statement: str

    model_config = ConfigDict(frozen=True)


class OperationalHighlightItemDTO(BaseModel):
    highlight_key: str
    title: str
    metric_value: str
    status: Literal["OPTIMAL", "ATTENTION", "CRITICAL", "INFO"]

    model_config = ConfigDict(frozen=True)


class EventItemDTO(BaseModel):
    event_id: str
    timestamp: str
    event_type: Literal["SLA_BREACH", "QUEUE_OVERFLOW", "ERP_IMPORT_COMPLETE", "ERP_IMPORT_FAILED", "LONG_DELAY"]
    category_icon: str
    title: str
    description: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "INFO"]

    model_config = ConfigDict(frozen=True)


class DataQualityItemDTO(BaseModel):
    issue_category: str
    issue_count: int
    status: Literal["PASS", "ATTENTION", "FAILED"]
    impact_description: str
    suggested_action: str

    model_config = ConfigDict(frozen=True)


class OperationalWidgetsResponseDTO(BaseModel):
    dashboard_health: DashboardHealthDTO
    readiness: list[SystemReadinessItemDTO]
    highlights: list[OperationalHighlightItemDTO]
    events: list[EventItemDTO]
    data_quality: list[DataQualityItemDTO]

    model_config = ConfigDict(frozen=True)
