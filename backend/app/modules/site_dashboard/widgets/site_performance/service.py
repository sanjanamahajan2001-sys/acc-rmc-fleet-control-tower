"""
Site Performance Service Layer
Workstream 2.7 Service
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.widgets.site_performance.repository import SitePerformanceRepository
from app.modules.site_dashboard.widgets.site_performance.calculations import SitePerformanceCalculations
from app.modules.site_dashboard.widgets.site_performance.dtos import SitePerformanceResponseDTO


class SitePerformanceService:
    """Orchestrates SQL queries and SLA performance calculations."""

    @staticmethod
    async def get_site_performance(session: AsyncSession, filters: dict[str, Any]) -> SitePerformanceResponseDTO:
        raw_metrics = await SitePerformanceRepository.get_performance_aggregates(session, filters)
        summary, delays, insights = SitePerformanceCalculations.compute_performance(raw_metrics)

        return SitePerformanceResponseDTO(
            summary=summary,
            delay_distribution=delays,
            insights=insights,
        )
