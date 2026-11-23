"""
Operational Widgets REST API Router
Workstream 2.10 Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.widgets.operational_widgets.dtos import OperationalWidgetsResponseDTO
from app.modules.site_dashboard.widgets.operational_widgets.service import OperationalWidgetsService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard/operational-widgets", tags=["Site Dashboard Operational Widgets"])


@router.get("", response_model=APIResponse[OperationalWidgetsResponseDTO])
async def get_operational_widgets(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[OperationalWidgetsResponseDTO]:
    normalized_filters = {
        "plant_id": params.plant_id or "ALL",
        "customer_id": params.customer_id or "ALL",
        "dataset_type": params.dataset_type or "ALL",
    }
    data = await OperationalWidgetsService.get_operational_widgets(session, normalized_filters)
    return envelope.success(data)
