"""
TM Details REST API Router
Workstream 2.6 Routes
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.widgets.tm_details.dtos import TMDetailsResponseDTO
from app.modules.site_dashboard.widgets.tm_details.service import TMDetailsService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard/tm-details", tags=["Site Dashboard TM Details"])


@router.get("", response_model=APIResponse[TMDetailsResponseDTO])
async def get_tm_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=5000),
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[TMDetailsResponseDTO]:
    normalized_filters = {
        "plant_id": params.plant_id or "ALL",
        "customer_id": params.customer_id or "ALL",
        "dataset_type": params.dataset_type or "ALL",
    }
    data = await TMDetailsService.get_tm_details(session, normalized_filters, page, page_size)
    return envelope.success(data)
