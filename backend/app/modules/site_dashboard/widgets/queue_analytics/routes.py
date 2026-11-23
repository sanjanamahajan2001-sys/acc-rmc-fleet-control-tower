"""
Queue Analytics REST API Endpoint
Workstream 2.5 Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.widgets.queue_analytics.dto import QueueAnalyticsResponseDTO
from app.modules.site_dashboard.widgets.queue_analytics.service import QueueAnalyticsService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard/queue-analytics", tags=["Site Dashboard Queue Analytics"])


@router.get("", response_model=APIResponse[QueueAnalyticsResponseDTO])
async def get_queue_analytics(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[QueueAnalyticsResponseDTO]:
    normalized_filters = {
        "plant_id": params.plant_id or "ALL",
        "customer_id": params.customer_id or "ALL",
        "dataset_type": params.dataset_type or "ALL",
    }
    data = await QueueAnalyticsService.compute_queue_analytics(session, normalized_filters)
    return envelope.success(data)
