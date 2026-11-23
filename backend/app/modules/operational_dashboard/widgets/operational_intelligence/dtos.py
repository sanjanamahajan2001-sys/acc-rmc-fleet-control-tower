from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


class OperationalIntelligenceStatusEnum(str, Enum):
    AVAILABLE = "AVAILABLE"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    UNAVAILABLE = "UNAVAILABLE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class OperationalGradeEnum(str, Enum):
    GRADE_A = "GRADE_A"
    GRADE_B = "GRADE_B"
    GRADE_C = "GRADE_C"
    GRADE_D = "GRADE_D"


class ProblemCustomerDTO(BaseModel):
    customer_id: str = Field(..., description="Canonical customer code or ID")
    customer_name: str = Field(..., description="Customer display name")
    rank: int = Field(..., description="1-indexed rank order")
    total_trips: int = Field(..., description="Total dispatches under active filter")
    holding_hours: float = Field(..., description="Total holding penalty hours (t2a > 20m)")
    retention_hours: float = Field(..., description="Total retention penalty hours (t2c > 10m)")
    total_lost_hours: float = Field(..., description="Holding + Retention penalty hours")
    cei: float = Field(..., description="Customer Efficiency Index score (0-100)")


class ProblemCustomerListResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    total_count: int = Field(..., description="Total customer records found")
    data: List[ProblemCustomerDTO] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)


class OverlapSiteDTO(BaseModel):
    site_id: str = Field(..., description="Canonical customer/site code or ID")
    site_name: str = Field(..., description="Site display name")
    rank: int = Field(..., description="1-indexed rank order by weighted TM-mins")
    total_trips: int = Field(..., description="Total dispatches for site")
    peak_tms_together: int = Field(..., description="Peak concurrent TMs at site")
    avg_tms_standing_together: float = Field(..., description="Average concurrent TMs during overlap")
    overlap_hours: float = Field(..., description="Total overlap duration in hours")
    weighted_tm_minutes: float = Field(..., description="Weighted TM-minutes (concurrency - 1) * duration")


class OverlapHeatmapResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    total_sites: int = Field(..., description="Total overlapping sites found")
    data: List[OverlapSiteDTO] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)


class SiteReadinessDTO(BaseModel):
    site_id: str = Field(..., description="Canonical site/customer code or ID")
    site_name: str = Field(..., description="Site display name")
    rank: int = Field(..., description="1-indexed rank order by SRI score")
    total_trips: int = Field(..., description="Total dispatches for site")
    swi_site: float = Field(..., description="Site Waiting Index (0-100)")
    dpi_site: float = Field(..., description="Site Dispatch Planning Index (0-100)")
    fui_site: float = Field(..., description="Site Fleet Utilization ratio (0-100)")
    sri_score: float = Field(..., description="Composite Site Readiness Index score (0-100)")
    grade: OperationalGradeEnum = Field(..., description="Operational Grade (A, B, C, D)")


class SiteReadinessResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    total_sites: int = Field(..., description="Total site records evaluated")
    data: List[SiteReadinessDTO] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)


# --- WS-03.3 Holding & Retention Overview DTOs ---

class HoldingRetentionTrendPointDTO(BaseModel):
    hour_label: str = Field(..., description="24-hour bucket label (00:00 to 23:00)")
    total_dispatches: int = Field(..., description="Dispatches arriving in hour")
    holding_penalty_mins: float = Field(..., description="Total holding penalty minutes in hour")
    retention_penalty_mins: float = Field(..., description="Total retention penalty minutes in hour")
    total_lost_hours: float = Field(..., description="Total lost hours (holding + retention mins / 60.0)")


class HoldingRetentionSummaryDTO(BaseModel):
    total_dispatches: int = Field(..., description="Total dispatches under active filter")
    total_holding_penalty_mins: float = Field(..., description="Total holding penalty minutes")
    total_retention_penalty_mins: float = Field(..., description="Total retention penalty minutes")
    total_lost_hours: float = Field(..., description="Total lost hours across scope")


class HoldingRetentionResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    summary: HoldingRetentionSummaryDTO = Field(..., description="Aggregate summary metrics")
    data: List[HoldingRetentionTrendPointDTO] = Field(default_factory=list, description="24 hourly trend points")
    filters: Dict[str, Any] = Field(default_factory=dict)


# --- WS-03.4 Dispatch Accuracy Score (DAS) Overview & Detail DTOs ---

class DASBucketBreakdownDTO(BaseModel):
    within_20m_count: int = Field(..., description="Dispatches with t2a <= 20.0m")
    within_20m_pct: float = Field(..., description="Percentage of total dispatches within 20m")
    range_21_40m_count: int = Field(0, description="Dispatches with 20.0m < t2a <= 40.0m")
    range_21_40m_pct: float = Field(0.0, description="Percentage of total dispatches 21-40m")
    range_41_60m_count: int = Field(0, description="Dispatches with 40.0m < t2a <= 60.0m")
    range_41_60m_pct: float = Field(0.0, description="Percentage of total dispatches 41-60m")
    above_60m_count: int = Field(0, description="Dispatches with t2a > 60.0m")
    above_60m_pct: float = Field(0.0, description="Percentage of total dispatches > 60m")
    moderate_20_40m_count: int = Field(..., description="Dispatches with 20.0m < t2a <= 40.0m")
    moderate_20_40m_pct: float = Field(..., description="Percentage of total dispatches 20-40m")
    critical_above_40m_count: int = Field(..., description="Dispatches with t2a > 40.0m")
    critical_above_40m_pct: float = Field(..., description="Percentage of total dispatches > 40m")


class DASSummaryDTO(BaseModel):
    total_dispatches: int = Field(..., description="Total dispatches under active filter")
    accurate_dispatches: int = Field(..., description="Accurate dispatches (t2a <= 20.0m)")
    das_score: Optional[float] = Field(None, description="Dispatch Accuracy Score percentage (0-100)")
    target_sla: float = Field(90.0, description="SLA target percentage")
    variance: Optional[float] = Field(None, description="Variance from target SLA")
    operational_status: str = Field(..., description="OPTIMAL, WARNING, CRITICAL, or NEUTRAL")


class DASOverviewResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    summary: DASSummaryDTO = Field(..., description="Aggregate DAS summary metrics")
    buckets: DASBucketBreakdownDTO = Field(..., description="3-bucket delay breakdown")
    filters: Dict[str, Any] = Field(default_factory=dict)


class DASDetailRowDTO(BaseModel):
    customer_id: str = Field(..., description="Canonical customer code or ID")
    customer_name: str = Field(..., description="Customer display name")
    rank: int = Field(..., description="1-indexed rank order by lowest DAS score")
    total_dispatches: int = Field(..., description="Total dispatches for customer")
    accurate_count: int = Field(..., description="Accurate dispatches (t2a <= 20m)")
    moderate_count: int = Field(..., description="Moderate delay dispatches (20-40m)")
    critical_count: int = Field(..., description="Critical delay dispatches (>40m)")
    das_score: float = Field(..., description="Dispatch Accuracy Score percentage (0-100)")
    within_20m_pct: float = Field(..., description="Percentage of trips within 20m")
    moderate_pct: float = Field(..., description="Percentage of trips 20-40m")
    critical_pct: float = Field(..., description="Percentage of trips >40m")
    operational_status: str = Field(..., description="OPTIMAL, WARNING, or CRITICAL")


class DASDetailsResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    total_customers: int = Field(..., description="Total customer breakdown rows")
    summary: DASSummaryDTO = Field(..., description="Aggregate DAS summary metrics")
    buckets: DASBucketBreakdownDTO = Field(..., description="Aggregate 3-bucket delay breakdown")
    data: List[DASDetailRowDTO] = Field(default_factory=list, description="Customer-level DAS detail rows")
    filters: Dict[str, Any] = Field(default_factory=dict)


class PotentialImpactCategoryDTO(BaseModel):
    reduction_pct: float = Field(20.0, description="Holding or Retention target reduction percentage")
    saved_hours_total: float = Field(..., description="Total cumulative scope hours saved")
    trips_unlocked: int = Field(..., description="Equivalent dispatches/trips unlocked (saved_hours * 0.8)")


class TotalPotentialImpactDTO(BaseModel):
    saved_hours_total: float = Field(..., description="Total cumulative scope hours saved (holding + retention)")
    total_trips_unlocked: int = Field(..., description="Total dispatches/trips unlocked (holding + retention trips)")


class PotentialImpactResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    data: Dict[str, Any] = Field(..., description="Holding, retention, and total impact metrics")
    filters: Dict[str, Any] = Field(default_factory=dict)


class CustomerEfficiencyDTO(BaseModel):
    rank: int = Field(..., description="1-indexed rank order by lowest CEI score")
    customer_id: str = Field(..., description="Canonical customer code or ID")
    customer_name: str = Field(..., description="Customer display name")
    cei_score: float = Field(..., description="Customer Efficiency Index score (0-100)")
    grade: str = Field(..., description="Good, Needs Improvement, or Critical")
    trend: str = Field("FLAT", description="Trend direction (FLAT)")
    total_trips: int = Field(..., description="Total dispatches under active filter")
    holding_penalty_mins: float = Field(..., description="Total holding penalty minutes (t2a > 20m)")
    retention_penalty_mins: float = Field(..., description="Total retention penalty minutes (t2c > 10m)")


class CustomerEfficiencyResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    data: List[CustomerEfficiencyDTO] = Field(default_factory=list, description="Customer-level CEI rows")
    filters: Dict[str, Any] = Field(default_factory=dict)


class SiteComparisonDTO(BaseModel):
    rank: int = Field(..., description="1-indexed rank order by highest dispatches / site performance")
    site_code: str = Field(..., description="Canonical site/plant code")
    site_name: str = Field(..., description="Site/plant display name")
    dispatches: int = Field(..., description="Total qualified trip count")
    volume_cum: float = Field(..., description="Total delivered volume in cubic meters (m3)")
    avg_holding_mins: float = Field(..., description="Mean site holding time in minutes")
    avg_retention_mins: float = Field(..., description="Mean site retention time in minutes")
    max_queue_tms: int = Field(..., description="Maximum simultaneous TMs at site")
    dispatch_accuracy: float = Field(..., description="Dispatch Accuracy Score percentage (0-100)")
    status: str = Field(..., description="Operational status: Optimal, Good, Warning, or Critical")


class SiteComparisonResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum = OperationalIntelligenceStatusEnum.AVAILABLE
    data: List[SiteComparisonDTO] = Field(default_factory=list, description="Site-level comparison rows")
    filters: Dict[str, Any] = Field(default_factory=dict)



