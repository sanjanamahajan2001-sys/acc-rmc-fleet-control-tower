from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPIRibbonResponseDTO,
    KPIRibbonContainerDTO,
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.repository import KPIRepository
from app.modules.operational_dashboard.widgets.kpis.services.dispatch_accuracy import DispatchAccuracyEngine
from app.modules.operational_dashboard.widgets.kpis.services.swi import SWIEngine
from app.modules.operational_dashboard.widgets.kpis.services.dpi import DPIEngine
from app.modules.operational_dashboard.widgets.kpis.services.fui import FUIEngine
from app.modules.operational_dashboard.widgets.kpis.services.total_dispatches import TotalDispatchesEngine


class ExecutiveKPIService:
    """
    Master Orchestration Service for WS-03.1 Executive KPIRibbon.
    Reuses WS-03.0 context semantics & delegates to isolated KPI engines.
    Contains ZERO business formulas itself.
    """

    @staticmethod
    async def get_kpi_ribbon(session: AsyncSession, params: DashboardFilterParams) -> KPIRibbonResponseDTO:
        # 1. Reuse WS-03.0 context service to obtain canonical dataset envelope
        shell_context = await OperationalContextService.get_shell_context(session, params)
        context_env = shell_context.context

        filter_dict = {
            "plant_id": params.plant_id or "ALL",
            "customer_id": params.customer_id or "ALL",
            "dataset_type": (params.dataset_type or "ALL").upper(),
        }

        # 2. Fetch raw SQL aggregation metrics for Dispatch Accuracy (KPI 1)
        accuracy_metrics = await KPIRepository.get_dispatch_accuracy_metrics(session, filter_dict)
        accuracy_dto = DispatchAccuracyEngine().calculate(accuracy_metrics)

        # 3. Fetch raw SQL aggregation metrics for Site Waiting Index SWI (KPI 2)
        swi_metrics = await KPIRepository.get_swi_metrics(session, filter_dict)
        swi_dto = SWIEngine().calculate(swi_metrics)

        # 4. Fetch raw DPI observations and delegate to DPIEngine (KPI 3)
        dpi_obs = await KPIRepository.get_dpi_observations(session, filter_dict)
        dpi_dto = DPIEngine().calculate(dpi_obs)

        # 5. Fetch raw FUI metrics and delegate to FUIEngine (KPI 4)
        fui_metrics = await KPIRepository.get_fui_metrics(session, filter_dict)
        fui_dto = FUIEngine().calculate(fui_metrics)

        # 6. Fetch raw total dispatch count and delegate to TotalDispatchesEngine (KPI 5)
        total_count = await KPIRepository.get_total_dispatch_count(session, filter_dict)
        total_dto = TotalDispatchesEngine().calculate(total_count)

        # 7. Assemble DTO container
        container = KPIRibbonContainerDTO(
            dispatch_accuracy=accuracy_dto,
            swi=swi_dto,
            dpi=dpi_dto,
            fui=fui_dto,
            total_dispatches=total_dto,
        )

        return KPIRibbonResponseDTO(context=context_env, kpis=container)
