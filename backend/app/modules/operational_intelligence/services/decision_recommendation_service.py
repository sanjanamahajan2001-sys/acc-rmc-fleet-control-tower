"""
WS-09 Section 03 Decision Recommendation Backend Adapter Service
Consumes canonical DecisionIntelligenceRepository and RecommendationEngine authority directly.
"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.site_dashboard.widgets.decision_intelligence.repository import DecisionIntelligenceRepository
from app.modules.site_dashboard.widgets.decision_intelligence.recommendation_engine import RecommendationEngine
from app.modules.operational_intelligence.schemas.decision_recommendation_dtos import (
    DecisionSummaryCountsDTO,
    RecommendationItemDTO,
    DecisionInsightItemDTO,
    OperationalDecisionRecommendationResponseDTO,
)


class OperationalDecisionRecommendationService:
    """
    Canonical Adapter Service for WS-09 Section 03 Decision Recommendations.
    Consumes DecisionIntelligenceRepository and RecommendationEngine authority directly.
    """

    @classmethod
    async def get_decision_recommendations(
        cls,
        session: AsyncSession,
        params: DashboardFilterParams,
    ) -> OperationalDecisionRecommendationResponseDTO:
        # 1. Resolve shell context & active dataset ID
        shell_context = await OperationalContextService.get_shell_context(session, params)
        context_env = shell_context.context

        effective_plant = params.plant_id or "ALL"
        effective_customer = params.customer_id or "ALL"
        effective_dataset = params.dataset_id or context_env.dataset_id or "DS-20260805-001"

        filters = {
            "plant_id": effective_plant,
            "customer_id": effective_customer,
            "dataset_id": effective_dataset,
        }

        # 2. Fetch raw operational metrics using canonical DecisionIntelligenceRepository
        raw_metrics = await DecisionIntelligenceRepository.get_operational_metrics(session, filters)

        # 3. Invoke canonical RecommendationEngine
        engine_summary, engine_recs, engine_insights = RecommendationEngine.generate_recommendations(
            raw_metrics=raw_metrics,
            filters=filters,
        )

        summary_dto = DecisionSummaryCountsDTO(
            active_recommendations=engine_summary.active_recommendations,
            high_priority_issues=engine_summary.high_priority_issues,
            estimated_delay_reduction_mins=engine_summary.estimated_delay_reduction_mins,
            estimated_sla_recovery_pct=engine_summary.estimated_sla_recovery_pct,
            fleet_efficiency_opportunity_pct=engine_summary.fleet_efficiency_opportunity_pct,
        )

        recommendation_items: List[RecommendationItemDTO] = [
            RecommendationItemDTO(
                recommendation_id=r.recommendation_id,
                priority=r.priority,
                recommendation_text=r.recommendation_text,
                underlying_reason=r.underlying_reason,
                affected_plant=r.affected_plant,
                affected_vehicle=r.affected_vehicle if r.affected_vehicle else None,
                expected_impact=r.expected_impact,
                confidence_pct=r.confidence_pct,
                status=r.status,
            )
            for r in engine_recs
        ]

        insight_items: List[DecisionInsightItemDTO] = [
            DecisionInsightItemDTO(
                title=i.title,
                category=i.category,
                action_type=i.action_type,
                description=i.description,
                urgency=i.urgency,
            )
            for i in engine_insights
        ]

        filter_desc = f"Plant: {effective_plant}, Customer: {effective_customer}, Dataset: {effective_dataset}"
        return OperationalDecisionRecommendationResponseDTO(
            summary=summary_dto,
            recommendations=recommendation_items,
            insights=insight_items,
            calculation_status="SUCCESS" if engine_summary.active_recommendations > 0 else "NO_RECORDS",
            calculation_notes=f"Authoritative RecommendationEngine calculation successful across {engine_summary.active_recommendations} active recommendations ({filter_desc}).",
        )
