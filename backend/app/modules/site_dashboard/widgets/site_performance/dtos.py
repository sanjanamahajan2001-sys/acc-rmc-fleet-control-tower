"""
Site Performance DTO Specifications
Workstream 2.7 Backend DTOs
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class PerformanceSummaryDTO(BaseModel):
    total_dispatches: int
    within_sla_count: int
    outside_sla_count: int
    compliance_pct: float
    violation_pct: float
    avg_holding_mins: float
    percentile_95_holding_mins: float
    max_holding_mins: float
    avg_retention_mins: float
    max_retention_mins: float
    avg_site_time_mins: float

    model_config = ConfigDict(frozen=True)


class DelayCategoryDTO(BaseModel):
    severity: Literal["Low", "Medium", "High", "Critical"]
    count: int
    percentage: float

    model_config = ConfigDict(frozen=True)


class InsightItemDTO(BaseModel):
    category: str
    title: str
    impact_level: Literal["High", "Medium", "Low"]
    insight_text: str

    model_config = ConfigDict(frozen=True)


class SitePerformanceResponseDTO(BaseModel):
    summary: PerformanceSummaryDTO
    delay_distribution: list[DelayCategoryDTO]
    insights: list[InsightItemDTO]

    model_config = ConfigDict(frozen=True)
