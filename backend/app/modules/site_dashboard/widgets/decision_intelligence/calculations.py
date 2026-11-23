"""
Decision Intelligence Calculations Engine wrapper
Workstream 2.9 Calculations Engine
"""

from typing import Any
from app.modules.site_dashboard.widgets.decision_intelligence.recommendation_engine import RecommendationEngine
from app.modules.site_dashboard.widgets.decision_intelligence.dtos import (
    DecisionSummaryDTO,
    RecommendationRowDTO,
    DecisionInsightCardDTO,
)


class DecisionIntelligenceCalculations:
    """Wrapper around RecommendationEngine for Decision Intelligence calculations."""

    @staticmethod
    def compute_decision_intelligence(
        raw_metrics: dict[str, Any],
        filters: dict[str, Any]
    ) -> tuple[DecisionSummaryDTO, list[RecommendationRowDTO], list[DecisionInsightCardDTO]]:
        return RecommendationEngine.generate_recommendations(raw_metrics, filters)
