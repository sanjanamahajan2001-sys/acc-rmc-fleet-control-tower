from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.operational_dashboard.context.dtos import ShellContextResponseDTO
from app.modules.operational_dashboard.widgets.kpis.orchestration_service import ExecutiveKPIService
from app.modules.operational_dashboard.widgets.kpis.dtos import KPIRibbonResponseDTO
from app.modules.operational_dashboard.widgets.operational_intelligence.services.problem_customers import ProblemCustomersEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.overlap_heatmap import OverlapHeatmapEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness import SiteReadinessEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.holding_retention import HoldingRetentionEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_overview import DASOverviewEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_details import DASDetailsEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.potential_impact import PotentialImpactEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.customer_efficiency import CustomerEfficiencyEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_comparison import SiteComparisonEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    ProblemCustomerListResponseDTO,
    OverlapHeatmapResponseDTO,
    SiteReadinessResponseDTO,
    HoldingRetentionResponseDTO,
    DASOverviewResponseDTO,
    DASDetailsResponseDTO,
    PotentialImpactResponseDTO,
    CustomerEfficiencyResponseDTO,
    SiteComparisonResponseDTO,
)



router = APIRouter(prefix="/operational-dashboard", tags=["Operational Dashboard"])


@router.get(
    "/context",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Shell Context Envelope (WS-03.0)",
    description="Returns shell context envelope, dataset metadata, available plants, and available customers.",
)
async def get_operational_dashboard_context(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: ShellContextResponseDTO = await OperationalContextService.get_shell_context(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/kpis",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Executive KPI Ribbon Container (WS-03.1)",
    description="Returns executive KPI ribbon metrics (Dispatch Accuracy, SWI, DPI, FUI, Total Dispatches).",
)
async def get_executive_kpis(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: KPIRibbonResponseDTO = await ExecutiveKPIService.get_kpi_ribbon(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/problem-customers",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Top 10 Problem Customers (WS-03.2 Widget 1)",
    description="Returns problem customers ranked by total lost hours (holding + retention penalty).",
)
@router.get(
    "/top-problem-customers",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Top 10 Problem Customers (WS-03.2 Widget 1)",
    description="Returns problem customers ranked by total lost hours (holding + retention penalty).",
)
async def get_top_problem_customers(
    limit: int | None = None,
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: ProblemCustomerListResponseDTO = await ProblemCustomersEngine.get_top_problem_customers(
        session, filters, limit=limit
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/overlap-heatmap",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Overlap Heat Map Analysis (WS-03.2 Widget 2)",
    description="Returns site overlap intensity analysis ranked by weighted TM-minutes.",
)
async def get_overlap_heatmap(
    limit: int | None = None,
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: OverlapHeatmapResponseDTO = await OverlapHeatmapEngine.get_overlap_heatmap(
        session, filters, limit=limit
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/site-readiness",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Site Readiness Index (SRI) Analysis (WS-03.2 Widget 3)",
    description="Returns site readiness scores and grade classifications under active filters.",
)
async def get_site_readiness(
    limit: int | None = None,
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: SiteReadinessResponseDTO = await SiteReadinessEngine.get_site_readiness(
        session, filters, limit=limit
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/holding-retention",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Holding & Retention Overview (WS-03.3)",
    description="Returns aggregate holding/retention penalties and 24 hourly trend points under active filters.",
)
async def get_holding_retention(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: HoldingRetentionResponseDTO = await HoldingRetentionEngine.evaluate_overview(
        session, filters
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/das-overview",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Dispatch Accuracy Score (DAS) Overview (WS-03.4)",
    description="Returns DAS score percentage, SLA target, variance, and 3-bucket delay classification.",
)
async def get_das_overview(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: DASOverviewResponseDTO = await DASOverviewEngine.evaluate_overview(
        session, filters
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/das-details",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Dispatch Accuracy Score (DAS) Details (WS-03.4 Phase 3M Gap Closure)",
    description="Returns customer-level DAS score percentages, delay breakdown counts, and operational rankings.",
)
async def get_das_details(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: DASDetailsResponseDTO = await DASDetailsEngine.evaluate_details(
        session, filters
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/potential-impact",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Potential Impact of Better Planning (WS-03.5 Phase 2)",
    description="Returns hours saved and equivalent trips unlocked under 20% holding/retention reduction.",
)
async def get_potential_impact(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: PotentialImpactResponseDTO = await PotentialImpactEngine.evaluate_impact(
        session, filters
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/customer-efficiency",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Customer Efficiency Index (CEI) Metrics (WS-03.6 Phase 2)",
    description="Returns customer-level Customer Efficiency Index scores, grades, trends, and deterministic operational rankings.",
)
async def get_customer_efficiency(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: CustomerEfficiencyResponseDTO = await CustomerEfficiencyEngine.get_customer_efficiency(
        session, filters
    )
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/site-comparison",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Site Comparison & Benchmarking Metrics (WS-04 Phase 2)",
    description="Returns site-level comparison metrics across dispatches, volume, holding, retention, queue, DAS, and status.",
)
async def get_site_comparison(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    filters = params.model_dump()
    dto: SiteComparisonResponseDTO = await SiteComparisonEngine.get_site_comparison(
        session, filters
    )
    return {"success": True, "data": dto.model_dump()}


