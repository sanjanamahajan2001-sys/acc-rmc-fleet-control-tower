"""
Canonical Dashboard DTO Registry
Workstream 2.0 Production DTOs
"""

import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict


class KPIItemDTO(BaseModel):
    key: str
    label: str
    current_value: float
    unit: Optional[str] = None
    threshold: Optional[float] = None
    target: Optional[float] = None
    variance: Optional[float] = None
    status: Literal["OPTIMAL", "WARNING", "CRITICAL"] = "OPTIMAL"
    trend: Literal["UP", "DOWN", "STABLE"] = "STABLE"

    model_config = ConfigDict(frozen=True)


class DashboardKPIDTO(BaseModel):
    dispatches: KPIItemDTO
    holding: KPIItemDTO
    retention: KPIItemDTO
    overlap: KPIItemDTO
    accuracy: KPIItemDTO
    unloading_60: Optional[KPIItemDTO] = None

    model_config = ConfigDict(frozen=True)



class TopSiteItemDTO(BaseModel):
    site_code: str
    site_name: str
    value: float
    unit: str

    model_config = ConfigDict(frozen=True)


class DashboardSummaryDTO(BaseModel):
    total_quantity_m3: float
    avg_holding_mins: float
    avg_retention_mins: float
    max_queue_tms: int
    queue_duration_mins: float
    total_overlap_mins: float
    weighted_overlap_tm_mins: float
    dispatch_accuracy_pct: float
    top_sites_holding: list[TopSiteItemDTO] = []
    top_sites_retention: list[TopSiteItemDTO] = []

    model_config = ConfigDict(frozen=True)


class TimelinePhaseDTO(BaseModel):
    phase: Literal["HOLDING", "UNLOADING", "RETENTION"]
    start_time: str
    end_time: str
    duration_mins: float

    model_config = ConfigDict(frozen=True)


class TMTimelineItemDTO(BaseModel):
    tm_no: str
    site_in: str
    unloading_start: str
    unloading_end: str
    site_out: str
    phases: list[TimelinePhaseDTO] = []

    model_config = ConfigDict(frozen=True)


class DashboardTimelineDTO(BaseModel):
    first_unloading_time: Optional[str] = None
    tm_timelines: list[TMTimelineItemDTO] = []

    model_config = ConfigDict(frozen=True)


class QueuePointDTO(BaseModel):
    timestamp: str
    active_queue_count: int

    model_config = ConfigDict(frozen=True)


class DashboardQueueDTO(BaseModel):
    avg_queue: float
    max_queue: int
    queue_duration_hours: float
    total_overlap_mins: float
    weighted_overlap_tm_mins: float
    points: list[QueuePointDTO] = []

    model_config = ConfigDict(frozen=True)


class CauseItemDTO(BaseModel):
    rule_code: str
    potential_reason: str
    impact_level: Literal["High", "Medium", "Low"]
    issue_type: str
    confidence_score: float
    evidence_statement: str

    model_config = ConfigDict(frozen=True)


class DashboardRootCauseDTO(BaseModel):
    causes: list[CauseItemDTO] = []

    model_config = ConfigDict(frozen=True)


class DashboardMetadataDTO(BaseModel):
    calculated_at: str
    cache_hit: bool = False
    calculation_duration_ms: float = 0.0
    source: str = "POSTGRESQL_CANONICAL"
    stale: bool = False
    api_version: str = "v1.0.0"
    schema_version: str = "v1.0"
    calculation_version: str = "v2.0"
    enabled_widgets: list[str] = [
        "KPI_CARDS",
        "SITE_SUMMARY",
        "GANTT_TIMELINE",
        "QUEUE_ANALYTICS",
        "HOLDING_DETAILS",
        "QUEUE_ARRIVAL",
        "DISPATCH_INTERVAL",
        "WAITING_VEHICLES",
        "ROOT_CAUSE",
    ]

    model_config = ConfigDict(frozen=True)


class SiteUnloadingLossRowDTO(BaseModel):
    rank: int
    customer_id: str
    customer_code: str
    customer_name: str
    affected_trips: int
    avg_excess_unloading_mins: float
    total_excess_unloading_mins: float
    total_excess_unloading_formatted: str
    diesel_overhead_cost: float

    model_config = ConfigDict(frozen=True)


class SiteUnloadingLossResponseDTO(BaseModel):
    total_affected_clients: int
    data: list[SiteUnloadingLossRowDTO] = []

    model_config = ConfigDict(frozen=True)


class SiteRetentionLossRowDTO(BaseModel):
    rank: int
    customer_id: str
    customer_code: str
    customer_name: str
    affected_trips: int
    avg_excess_retention_mins: float
    total_excess_retention_mins: float
    total_excess_retention_formatted: str

    model_config = ConfigDict(frozen=True)


class SiteRetentionLossResponseDTO(BaseModel):
    total_affected_clients: int
    data: list[SiteRetentionLossRowDTO] = []

    model_config = ConfigDict(frozen=True)


class SiteHoldingLossRowDTO(BaseModel):
    rank: int
    customer_id: str
    customer_code: str
    customer_name: str
    affected_trips: int
    avg_excess_holding_mins: float
    total_excess_holding_mins: float
    total_excess_holding_formatted: str
    diesel_overhead_cost: float

    model_config = ConfigDict(frozen=True)


class SiteHoldingLossResponseDTO(BaseModel):
    total_affected_clients: int
    data: list[SiteHoldingLossRowDTO] = []

    model_config = ConfigDict(frozen=True)


class MasterDashboardResponseDTO(BaseModel):
    calculated_at: str
    response_metadata: Optional[DashboardMetadataDTO] = None
    kpis: DashboardKPIDTO
    summary: DashboardSummaryDTO
    timeline: DashboardTimelineDTO
    queue: DashboardQueueDTO
    root_causes: DashboardRootCauseDTO
    diesel_economics: Optional[Any] = None

    model_config = ConfigDict(frozen=True)

