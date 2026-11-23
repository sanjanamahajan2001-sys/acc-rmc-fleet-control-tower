"""
Dashboard Data Orchestrator
Workstream 2.1 Request Lifecycle Coordinator
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.dto.canonical_dtos import MasterDashboardResponseDTO
from app.modules.site_dashboard.engine.calculation_engine import DashboardCalculationEngine
from app.modules.site_dashboard.orchestration.filter_engine import FilterEngine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams


class DashboardDataOrchestrator:
    """Coordinates Request Lifecycle, Cache Retrieval, and Engine Invocation."""

    @staticmethod
    async def get_master_dashboard_data(
        session: AsyncSession, params: DashboardFilterParams
    ) -> MasterDashboardResponseDTO:
        normalized_filters = FilterEngine.normalize_filters(params)
        return await DashboardCalculationEngine.compute_dashboard_metrics(session, normalized_filters)
