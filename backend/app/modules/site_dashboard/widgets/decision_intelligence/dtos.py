"""
Decision Intelligence DTO Specifications
Workstream 2.9 Backend DTOs
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class DecisionSummaryDTO(BaseModel):
    active_recommendations: int
    high_priority_issues: int
    estimated_delay_reduction_mins: float
    estimated_sla_recovery_pct: float
    fleet_efficiency_opportunity_pct: float

    model_config = ConfigDict(frozen=True)


class RecommendationRowDTO(BaseModel):
    recommendation_id: str
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    recommendation_text: str
    underlying_reason: str
    affected_plant: str
    affected_vehicle: str
    expected_impact: str
    confidence_pct: float
    status: Literal["Pending", "Applied", "Dismissed"]

    model_config = ConfigDict(frozen=True)


class DecisionInsightCardDTO(BaseModel):
    title: str
    category: str
    action_type: str
    description: str
    urgency: Literal["Immediate", "Scheduled", "Proactive"]

    model_config = ConfigDict(frozen=True)


class DecisionIntelligenceResponseDTO(BaseModel):
    summary: DecisionSummaryDTO
    recommendations: list[RecommendationRowDTO]
    insights: list[DecisionInsightCardDTO]

    model_config = ConfigDict(frozen=True)
