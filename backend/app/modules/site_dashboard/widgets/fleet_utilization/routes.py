"""
Fleet Utilization REST API Router
Workstream 2.8 Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.widgets.fleet_utilization.dtos import FleetUtilizationResponseDTO
from app.modules.site_dashboard.widgets.fleet_utilization.service import FleetUtilizationService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard/fleet-utilization", tags=["Site Dashboard Fleet Utilization"])


@router.get("", response_model=APIResponse[FleetUtilizationResponseDTO])
async def get_fleet_utilization(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[FleetUtilizationResponseDTO]:
    normalized_filters = {
        "plant_id": params.plant_id or "ALL",
        "customer_id": params.customer_id or "ALL",
        "dataset_type": params.dataset_type or "ALL",
    }
    data = await FleetUtilizationService.get_fleet_utilization(session, normalized_filters)
    return envelope.success(data)
