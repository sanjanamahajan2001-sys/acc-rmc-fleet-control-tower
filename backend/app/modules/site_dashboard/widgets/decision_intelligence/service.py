"""
Decision Intelligence Service Layer
Workstream 2.9 Service
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.widgets.decision_intelligence.repository import DecisionIntelligenceRepository
from app.modules.site_dashboard.widgets.decision_intelligence.calculations import DecisionIntelligenceCalculations
from app.modules.site_dashboard.widgets.decision_intelligence.dtos import DecisionIntelligenceResponseDTO


class DecisionIntelligenceService:
    """Orchestrates SQL queries and decision intelligence recommendation engine."""

    @staticmethod
    async def get_decision_intelligence(session: AsyncSession, filters: dict[str, Any]) -> DecisionIntelligenceResponseDTO:
        raw_metrics = await DecisionIntelligenceRepository.get_operational_metrics(session, filters)
        summary, recommendations, insights = DecisionIntelligenceCalculations.compute_decision_intelligence(raw_metrics, filters)

        return DecisionIntelligenceResponseDTO(
            summary=summary,
            recommendations=recommendations,
            insights=insights,
        )
