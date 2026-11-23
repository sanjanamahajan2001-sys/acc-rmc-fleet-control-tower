"""
WS-09 Section 03 Decision Recommendations DTO Schemas
Pass-through specifications mapped 1:1 to canonical RecommendationEngine DTOs.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class DecisionSummaryCountsDTO(BaseModel):
    active_recommendations: int = Field(..., description="Count of recommendations returned by RecommendationEngine")
    high_priority_issues: int = Field(..., description="Count of holding and retention SLA breaches")
    estimated_delay_reduction_mins: float = Field(..., description="Calculated queue delay reduction from engine")
    estimated_sla_recovery_pct: float = Field(..., description="Estimated SLA recovery percentage from engine")
    fleet_efficiency_opportunity_pct: float = Field(..., description="Fleet efficiency opportunity percentage from engine")


class RecommendationItemDTO(BaseModel):
    recommendation_id: str = Field(..., description="Direct pass-through of RecommendationEngine.recommendation_id")
    priority: str = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW")
    recommendation_text: str = Field(..., description="Direct pass-through of RecommendationEngine.recommendation_text")
    underlying_reason: str = Field(..., description="Direct pass-through of RecommendationEngine.underlying_reason")
    affected_plant: str = Field(..., description="Affected plant code or cluster name")
    affected_vehicle: Optional[str] = Field(default=None, description="Target mixer truck ID if vehicle-level")
    expected_impact: str = Field(..., description="Direct pass-through of RecommendationEngine.expected_impact")
    confidence_pct: float = Field(..., description="Direct pass-through of RecommendationEngine.confidence_pct")
    status: str = Field(..., description="Direct pass-through of RecommendationEngine.status")


class DecisionInsightItemDTO(BaseModel):
    title: str = Field(..., description="Insight title")
    category: str = Field(..., description="Insight category")
    action_type: str = Field(..., description="Action type")
    description: str = Field(..., description="Insight description")
    urgency: str = Field(..., description="Immediate | Scheduled | Proactive")


class OperationalDecisionRecommendationResponseDTO(BaseModel):
    summary: DecisionSummaryCountsDTO
    recommendations: List[RecommendationItemDTO]
    insights: List[DecisionInsightItemDTO]
    calculation_status: str = Field(default="SUCCESS", description="SUCCESS | NO_RECORDS | NOT_CONFIGURED | ERROR")
    calculation_notes: str = Field(..., description="Authoritative lineage and active filter context statement")
