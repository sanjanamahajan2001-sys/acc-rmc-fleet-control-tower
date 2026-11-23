"""
Fleet Utilization Service Layer
Workstream 2.8 Service
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.widgets.fleet_utilization.repository import FleetUtilizationRepository
from app.modules.site_dashboard.widgets.fleet_utilization.calculations import FleetUtilizationCalculations
from app.modules.site_dashboard.widgets.fleet_utilization.dtos import FleetUtilizationResponseDTO


class FleetUtilizationService:
    """Orchestrates SQL queries and vehicle fleet utilization calculations."""

    @staticmethod
    async def get_fleet_utilization(session: AsyncSession, filters: dict[str, Any]) -> FleetUtilizationResponseDTO:
        total_fleet, total_filtered_dispatches, vehicle_rows = await FleetUtilizationRepository.get_vehicle_aggregates(session, filters)
        summary, top_vehicles, alerts = FleetUtilizationCalculations.compute_fleet_intelligence(total_fleet, total_filtered_dispatches, vehicle_rows)

        return FleetUtilizationResponseDTO(
            summary=summary,
            top_vehicles=top_vehicles,
            alerts=alerts,
        )
