"""
FastAPI Site Dashboard REST API Router
Workstream 2.1 API Endpoints
"""

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.site_dashboard.dto.canonical_dtos import (
    MasterDashboardResponseDTO,
    DashboardKPIDTO,
    DashboardSummaryDTO,
    DashboardTimelineDTO,
    DashboardQueueDTO,
    DashboardRootCauseDTO,
    SiteUnloadingLossResponseDTO,
    SiteRetentionLossResponseDTO,
    SiteHoldingLossResponseDTO,
)
from app.modules.site_dashboard.services.site_unloading_loss_service import SiteUnloadingLossService
from app.modules.site_dashboard.services.site_retention_loss_service import SiteRetentionLossService
from app.modules.site_dashboard.services.site_holding_loss_service import SiteHoldingLossService
from app.modules.site_dashboard.orchestration.dashboard_orchestrator import DashboardDataOrchestrator
from app.modules.site_dashboard.schemas.request_dtos import (
    DashboardFilterParams,
    DashboardFilterMetadataResponseDTO,
)
from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/site-dashboard", tags=["Site Operational Intelligence Dashboard"])


@router.get("/filters", response_model=APIResponse[DashboardFilterMetadataResponseDTO])
async def get_dashboard_filters_metadata(
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DashboardFilterMetadataResponseDTO]:
    data = await DashboardFilterMetadataService.get_filter_metadata(session)
    return envelope.success(data)


@router.get("", response_model=APIResponse[MasterDashboardResponseDTO])
async def get_master_dashboard(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[MasterDashboardResponseDTO]:
    data = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
    return envelope.success(data)


@router.get("/kpis", response_model=APIResponse[DashboardKPIDTO])
async def get_dashboard_kpis(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DashboardKPIDTO]:
    data = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
    return envelope.success(data.kpis)


@router.get("/summary", response_model=APIResponse[DashboardSummaryDTO])
async def get_dashboard_summary(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DashboardSummaryDTO]:
    data = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
    return envelope.success(data.summary)


@router.get("/gantt", response_model=APIResponse[DashboardTimelineDTO])
async def get_dashboard_gantt(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DashboardTimelineDTO]:
    data = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
    return envelope.success(data.timeline)


@router.get("/queue", response_model=APIResponse[DashboardQueueDTO])
async def get_dashboard_queue(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DashboardQueueDTO]:
    data = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
    return envelope.success(data.queue)


@router.get("/root-cause", response_model=APIResponse[DashboardRootCauseDTO])
async def get_dashboard_root_cause(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[DashboardRootCauseDTO]:
    data = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
    return envelope.success(data.root_causes)


@router.get("/unloading-loss-breakdown", response_model=APIResponse[SiteUnloadingLossResponseDTO])
async def get_site_unloading_loss_breakdown(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[SiteUnloadingLossResponseDTO]:
    params_dict = params.model_dump()
    data = await SiteUnloadingLossService.get_unloading_loss_breakdown(session, params_dict)
    return envelope.success(data)


@router.get("/retention-loss-breakdown", response_model=APIResponse[SiteRetentionLossResponseDTO])
async def get_site_retention_loss_breakdown(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[SiteRetentionLossResponseDTO]:
    params_dict = params.model_dump()
    data = await SiteRetentionLossService.get_retention_loss_breakdown(session, params_dict)
    return envelope.success(data)


@router.get("/holding-loss-breakdown", response_model=APIResponse[SiteHoldingLossResponseDTO])
async def get_site_holding_loss_breakdown(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[SiteHoldingLossResponseDTO]:
    params_dict = params.model_dump()
    data = await SiteHoldingLossService.get_holding_loss_breakdown(session, params_dict)
    return envelope.success(data)
