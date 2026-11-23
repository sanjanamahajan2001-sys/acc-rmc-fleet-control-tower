"""
WS-09 Section 05 Fleet & Plant Operational Efficiency Backend Adapter Service
Composes canonical Fleet efficiency and CustomerEfficiencyEngine authority.
"""

from typing import List
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.operational_dashboard.widgets.operational_intelligence.services.customer_efficiency import CustomerEfficiencyEngine
from app.modules.erp.models import Dispatch, Vehicle, Plant, Customer
from app.modules.operational_intelligence.schemas.fleet_efficiency_dtos import (
    FleetEfficiencySummaryCountsDTO,
    PlantEfficiencyItemDTO,
    CustomerEfficiencyItemDTO,
    OperationalFleetEfficiencyResponseDTO,
)


class OperationalFleetEfficiencyService:
    """
    Canonical Adapter Service for WS-09 Section 05 Fleet & Plant Operational Efficiency.
    Composes PostgreSQL dispatches and CustomerEfficiencyEngine authority.
    """

    @classmethod
    def classify_grade(cls, score: float) -> str:
        if score >= 75.0:
            return "Good"
        elif score >= 50.0:
            return "Needs Improvement"
        else:
            return "Critical"

    @classmethod
    async def get_fleet_efficiency(
        cls,
        session: AsyncSession,
        params: DashboardFilterParams,
    ) -> OperationalFleetEfficiencyResponseDTO:
        # 1. Resolve shell context & active dataset ID
        shell_context = await OperationalContextService.get_shell_context(session, params)
        context_env = shell_context.context

        effective_plant = params.plant_id or "ALL"
        effective_customer = params.customer_id or "ALL"
        effective_dataset = params.dataset_id or context_env.dataset_id or "DS-20260805-001"

        filters = {
            "plant_id": effective_plant,
            "customer_id": effective_customer,
            "dataset_id": effective_dataset,
        }

        # 2. Query total active registered vehicles (Denominator for Utilization)
        q_total_vehs = select(func.count(Vehicle.id))
        total_active_vehs_res = (await session.execute(q_total_vehs)).scalar()
        total_active_vehs = max(1, total_active_vehs_res or 0)

        # 3. Query dispatches for dispatch-active vehicles, turnaround cycle, and holding/retention
        turnaround_expr = (
            func.coalesce(Dispatch.t1_transit_mins, 0.0)
            + func.coalesce(Dispatch.t2a_holding_mins, 0.0)
            + func.coalesce(Dispatch.t2b_unloading_mins, 0.0)
            + func.coalesce(Dispatch.t3_return_mins, 0.0)
        )

        q_summary = select(
            func.count(Dispatch.id).label("total_dispatches"),
            func.count(func.distinct(Dispatch.vehicle_id)).label("dispatch_active_vehs"),
            func.coalesce(func.avg(turnaround_expr), 0.0).label("avg_turnaround"),
            func.coalesce(func.avg(Dispatch.t2a_holding_mins), 0.0).label("avg_holding"),
            func.coalesce(func.avg(Dispatch.t2c_retention_mins), 0.0).label("avg_retention"),
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).join(Customer, Dispatch.customer_id == Customer.id, isouter=True)

        if effective_plant != "ALL":
            q_summary = q_summary.where(Plant.code == effective_plant)
        if effective_customer != "ALL":
            q_summary = q_summary.where(Customer.code == effective_customer)

        res_sum = (await session.execute(q_summary)).fetchone()

        total_dispatches = res_sum.total_dispatches if res_sum else 0
        dispatch_active_vehs = res_sum.dispatch_active_vehs if res_sum else 0
        avg_turnaround = float(res_sum.avg_turnaround if res_sum else 0.0)
        avg_holding = float(res_sum.avg_holding if res_sum else 0.0)
        avg_retention = float(res_sum.avg_retention if res_sum else 0.0)

        # 4. Calculate Fleet & Operational Index Components (decay function prevents negative clamp to 0)
        utilization_pct = min(100.0, round((dispatch_active_vehs / total_active_vehs) * 100.0, 1))
        # Turnaround Rating: 20m target = 100%. If holding is 30m, efficiency is ~66.7%
        turnaround_eff_pct = min(100.0, max(5.0, round((20.0 / max(20.0, avg_holding)) * 100.0, 1)))
        # Unloading Rating: 10m target = 100%. If retention is 15m, efficiency is ~66.7%
        unloading_eff_pct = min(100.0, max(5.0, round((10.0 / max(10.0, avg_retention)) * 100.0, 1)))

        overall_index = max(0.0, min(100.0, round(
            (0.40 * utilization_pct) + (0.30 * turnaround_eff_pct) + (0.30 * unloading_eff_pct),
            1
        )))

        summary_dto = FleetEfficiencySummaryCountsDTO(
            overall_efficiency_index=overall_index,
            fleet_utilization_pct=utilization_pct,
            avg_turnaround_time_mins=round(avg_turnaround, 1),
            avg_holding_time_mins=round(avg_holding, 1),
            avg_retention_time_mins=round(avg_retention, 1),
            turnaround_efficiency_pct=turnaround_eff_pct,
            site_unloading_efficiency_pct=unloading_eff_pct,
        )

        if total_dispatches == 0:
            return OperationalFleetEfficiencyResponseDTO(
                summary=summary_dto,
                plant_efficiency=[],
                customer_efficiency=[],
                calculation_status="NO_RECORDS",
                calculation_notes="No dispatch activity detected under the active filter context.",
            )

        # 5. Query Plant-Level Efficiency
        q_plant = select(
            Plant.code.label("plant_code"),
            Plant.name.label("plant_name"),
            func.count(func.distinct(Dispatch.vehicle_id)).label("active_vehs"),
            func.count(Dispatch.id).label("dispatches"),
            func.coalesce(func.avg(Dispatch.t2a_holding_mins), 0.0).label("avg_holding"),
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).join(Customer, Dispatch.customer_id == Customer.id, isouter=True)

        if effective_plant != "ALL":
            q_plant = q_plant.where(Plant.code == effective_plant)
        if effective_customer != "ALL":
            q_plant = q_plant.where(Customer.code == effective_customer)

        q_plant = q_plant.group_by(Plant.code, Plant.name).order_by(text("avg_holding DESC"), Plant.code.asc())
        res_plant = await session.execute(q_plant)

        plant_items: List[PlantEfficiencyItemDTO] = []
        for r in res_plant.fetchall():
            p_code = r.plant_code or "UNASSIGNED"
            p_name = r.plant_name or p_code
            p_holding = float(r.avg_holding)
            p_turnaround_eff = min(100.0, max(5.0, round((20.0 / max(20.0, p_holding)) * 100.0, 1)))
            plant_items.append(
                PlantEfficiencyItemDTO(
                    plant_code=p_code,
                    plant_name=p_name,
                    active_vehicles=int(r.active_vehs),
                    total_dispatches=int(r.dispatches),
                    avg_holding_mins=round(p_holding, 1),
                    turnaround_efficiency_pct=p_turnaround_eff,
                    efficiency_grade=cls.classify_grade(p_turnaround_eff),
                )
            )

        # 6. Re-use CustomerEfficiencyEngine 1:1 Authority for Customer CEI
        cei_res = await CustomerEfficiencyEngine.get_customer_efficiency(session, filters)
        customer_items: List[CustomerEfficiencyItemDTO] = []

        for cust in cei_res.data:
            # Customer Efficiency Score
            total_t = max(1, cust.total_trips)
            ret_mins = round((getattr(cust, "retention_penalty_mins", 0.0) or 0.0) / total_t, 1)
            # Safe CEI score fallback
            score = round(float(cust.cei_score), 1) if getattr(cust, "cei_score", None) is not None else min(100.0, max(10.0, round((10.0 / max(10.0, ret_mins)) * 100.0, 1)))
            customer_items.append(
                CustomerEfficiencyItemDTO(
                    customer_code=cust.customer_id,
                    customer_name=cust.customer_name,
                    total_trips=cust.total_trips,
                    avg_retention_mins=ret_mins,
                    cei_score=score,
                    efficiency_grade=cls.classify_grade(score),
                )
            )

        filter_desc = f"Plant: {effective_plant}, Customer: {effective_customer}, Dataset: {effective_dataset}"
        return OperationalFleetEfficiencyResponseDTO(
            summary=summary_dto,
            plant_efficiency=plant_items,
            customer_efficiency=customer_items,
            calculation_status="SUCCESS",
            calculation_notes=f"Authoritative fleet efficiency calculation successful across {utilization_pct}% utilization ({filter_desc}).",
        )
