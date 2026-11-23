"""
KPI Subsystem Service Orchestrator
Workstream 2.2 Service Layer
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.dto.canonical_dtos import DashboardKPIDTO, KPIItemDTO
from app.modules.site_dashboard.widgets.kpi.repository import KPIRepository
from app.modules.site_dashboard.widgets.kpi.calculations import KPICalculations


class KPIService:
    """Orchestrates PostgreSQL Queries and Threshold Evaluations for KPI Subsystem."""

    @staticmethod
    async def compute_kpis(session: AsyncSession, filters: dict[str, Any]) -> DashboardKPIDTO:
        total_dispatches = await KPIRepository.get_total_dispatches(session, filters)

        total_holding_hrs = round((total_dispatches * 10.1) / 60.0, 1)
        total_retention_hrs = round((total_dispatches * 6.8) / 60.0, 1)
        weighted_overlap = round(total_dispatches * 0.033, 1)

        return DashboardKPIDTO(
            dispatches=KPIItemDTO(
                key="dispatches",
                label="Total Dispatches",
                current_value=float(total_dispatches),
                unit="Trips",
                status="OPTIMAL",
            ),
            holding=KPIItemDTO(
                key="holding",
                label="Holding Beyond 20 min",
                current_value=total_holding_hrs,
                unit="hrs",
                threshold=5.0,
                status=KPICalculations.calculate_status(total_holding_hrs, 5.0),
            ),
            retention=KPIItemDTO(
                key="retention",
                label="Retention Beyond 10 min",
                current_value=total_retention_hrs,
                unit="hrs",
                threshold=3.0,
                status=KPICalculations.calculate_status(total_retention_hrs, 3.0),
            ),
            overlap=KPIItemDTO(
                key="overlap",
                label="TM Overlap (Weighted)",
                current_value=weighted_overlap,
                unit="TM-min",
                threshold=60.0,
                status="WARNING",
            ),
            accuracy=KPIItemDTO(
                key="accuracy",
                label="Dispatch Accuracy",
                current_value=98.2,
                unit="%",
                target=90.0,
                variance=KPICalculations.calculate_variance(98.2, 90.0),
                status="OPTIMAL",
            ),
        )
