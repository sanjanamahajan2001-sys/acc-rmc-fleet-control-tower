"""
Decision Intelligence REST API Router
Workstream 2.9 Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.widgets.decision_intelligence.dtos import DecisionIntelligenceResponseDTO
from app.modules.site_dashboard.widgets.decision_intelligence.service import DecisionIntelligenceService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard/decision-intelligence", tags=["Site Dashboard Decision Intelligence"])


@router.get("", response_model=APIResponse[DecisionIntelligenceResponseDTO])
async def get_decision_intelligence(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DecisionIntelligenceResponseDTO]:
    normalized_filters = {
        "plant_id": params.plant_id or "ALL",
        "customer_id": params.customer_id or "ALL",
        "dataset_type": params.dataset_type or "ALL",
    }
    data = await DecisionIntelligenceService.get_decision_intelligence(session, normalized_filters)
    return envelope.success(data)
