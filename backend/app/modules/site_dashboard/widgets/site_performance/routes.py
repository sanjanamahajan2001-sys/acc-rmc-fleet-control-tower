"""
Site Performance REST API Router
Workstream 2.7 Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.widgets.site_performance.dtos import SitePerformanceResponseDTO
from app.modules.site_dashboard.widgets.site_performance.service import SitePerformanceService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard/site-performance", tags=["Site Dashboard Performance"])


@router.get("", response_model=APIResponse[SitePerformanceResponseDTO])
async def get_site_performance(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[SitePerformanceResponseDTO]:
    normalized_filters = {
        "plant_id": params.plant_id or "ALL",
        "customer_id": params.customer_id or "ALL",
        "dataset_type": params.dataset_type or "ALL",
    }
    data = await SitePerformanceService.get_site_performance(session, normalized_filters)
    return envelope.success(data)
