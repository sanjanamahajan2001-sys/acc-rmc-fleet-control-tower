"""
WS-09 Section 04 Financial Loss & SLA Risk Exposure Backend Service
Queries PostgreSQL dispatches and platform settings to compute financial risk exposure.
"""

from typing import List
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.erp.models import Dispatch, Plant, Customer
from app.modules.operational_intelligence.schemas.financial_exposure_dtos import (
    FinancialSummaryCountsDTO,
    FinancialBreakdownItemDTO,
    EntityFinancialRiskItemDTO,
    OperationalFinancialExposureResponseDTO,
)

# Authoritative Financial Exposure Rates (INR per minute)
HOLDING_DELAY_COST_RATE_INR_PER_MIN: float = 25.0
RETENTION_SLA_PENALTY_RATE_INR_PER_MIN: float = 35.0
IDLE_FUEL_WASTE_RATE_INR_PER_MIN: float = 15.0


class OperationalFinancialExposureService:
    """
    Canonical Service for WS-09 Section 04 Financial Loss & SLA Risk Exposure.
    Computes holding loss, retention SLA penalty, and idle fuel waste from PostgreSQL dispatches.
    """

    @classmethod
    async def get_financial_exposure(
        cls,
        session: AsyncSession,
        params: DashboardFilterParams,
    ) -> OperationalFinancialExposureResponseDTO:
        # 1. Resolve shell context & active dataset ID
        shell_context = await OperationalContextService.get_shell_context(session, params)
        context_env = shell_context.context

        effective_plant = params.plant_id or "ALL"
        effective_customer = params.customer_id or "ALL"
        effective_dataset = params.dataset_id or context_env.dataset_id or "DS-20260805-001"

        # 2. Query dispatches for aggregate holding and retention penalty minutes
        holding_expr = func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)
        retention_expr = func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)

        q_summary = select(
            func.count(Dispatch.id).label("total_dispatches"),
            func.coalesce(func.sum(holding_expr), 0.0).label("holding_pen_mins"),
            func.coalesce(func.sum(retention_expr), 0.0).label("retention_pen_mins"),
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).join(Customer, Dispatch.customer_id == Customer.id, isouter=True)

        if effective_plant != "ALL":
            q_summary = q_summary.where(Plant.code == effective_plant)
        if effective_customer != "ALL":
            q_summary = q_summary.where(Customer.code == effective_customer)

        res_sum = (await session.execute(q_summary)).fetchone()

        total_dispatches = res_sum.total_dispatches if res_sum else 0
        holding_mins = float(res_sum.holding_pen_mins if res_sum else 0.0)
        retention_mins = float(res_sum.retention_pen_mins if res_sum else 0.0)
        total_pen_mins = holding_mins + retention_mins

        # 3. Calculate Financial Loss Components
        holding_cost = round(holding_mins * HOLDING_DELAY_COST_RATE_INR_PER_MIN, 2)
        retention_cost = round(retention_mins * RETENTION_SLA_PENALTY_RATE_INR_PER_MIN, 2)
        idle_fuel_cost = round(holding_mins * IDLE_FUEL_WASTE_RATE_INR_PER_MIN, 2)
        total_exposure = round(holding_cost + retention_cost + idle_fuel_cost, 2)

        summary_dto = FinancialSummaryCountsDTO(
            total_financial_exposure_inr=total_exposure,
            holding_delay_cost_inr=holding_cost,
            retention_sla_penalty_inr=retention_cost,
            idle_fuel_waste_inr=idle_fuel_cost,
            total_penalty_mins=round(total_pen_mins, 1),
        )

        if total_exposure == 0.0 and total_dispatches == 0:
            return OperationalFinancialExposureResponseDTO(
                summary=summary_dto,
                breakdown=[],
                top_plant_risk=[],
                top_customer_risk=[],
                calculation_status="NO_RECORDS",
                calculation_notes="No dispatch activity or financial exposure detected under the active filter context.",
            )

        # 4. Financial Breakdown Items
        breakdown_items: List[FinancialBreakdownItemDTO] = []
        if total_exposure > 0:
            breakdown_items = [
                FinancialBreakdownItemDTO(
                    category="PLANT_HOLDING",
                    label="Plant Holding Queue Financial Loss",
                    penalty_mins=round(holding_mins, 1),
                    cost_rate_per_min=HOLDING_DELAY_COST_RATE_INR_PER_MIN,
                    total_cost_inr=holding_cost,
                    percentage=round((holding_cost / total_exposure) * 100, 1),
                ),
                FinancialBreakdownItemDTO(
                    category="CUSTOMER_RETENTION",
                    label="Customer Site SLA Penalty Exposure",
                    penalty_mins=round(retention_mins, 1),
                    cost_rate_per_min=RETENTION_SLA_PENALTY_RATE_INR_PER_MIN,
                    total_cost_inr=retention_cost,
                    percentage=round((retention_cost / total_exposure) * 100, 1),
                ),
                FinancialBreakdownItemDTO(
                    category="IDLE_FUEL",
                    label="Idle Fuel Waste Exposure",
                    penalty_mins=round(holding_mins, 1),
                    cost_rate_per_min=IDLE_FUEL_WASTE_RATE_INR_PER_MIN,
                    total_cost_inr=idle_fuel_cost,
                    percentage=round((idle_fuel_cost / total_exposure) * 100, 1),
                ),
            ]

        # 5. Top Plant Financial Risk
        q_plant = select(
            Plant.code.label("plant_code"),
            func.coalesce(func.sum(holding_expr + retention_expr), 0.0).label("plant_pen_mins"),
            func.coalesce(func.sum(holding_expr * HOLDING_DELAY_COST_RATE_INR_PER_MIN + retention_expr * RETENTION_SLA_PENALTY_RATE_INR_PER_MIN + holding_expr * IDLE_FUEL_WASTE_RATE_INR_PER_MIN), 0.0).label("plant_exp_inr")
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).join(Customer, Dispatch.customer_id == Customer.id, isouter=True)

        if effective_plant != "ALL":
            q_plant = q_plant.where(Plant.code == effective_plant)
        if effective_customer != "ALL":
            q_plant = q_plant.where(Customer.code == effective_customer)

        q_plant = q_plant.group_by(Plant.code).order_by(text("plant_exp_inr DESC")).limit(5)
        res_plant = await session.execute(q_plant)
        plant_risk: List[EntityFinancialRiskItemDTO] = []
        for r in res_plant.fetchall():
            p_code = r.plant_code or "UNASSIGNED"
            plant_risk.append(
                EntityFinancialRiskItemDTO(
                    entity_type="PLANT",
                    entity_code=p_code,
                    entity_name=p_code,
                    penalty_mins=round(float(r.plant_pen_mins), 1),
                    financial_exposure_inr=round(float(r.plant_exp_inr), 2),
                )
            )

        # 6. Top Customer Financial Risk
        q_cust = select(
            Customer.code.label("cust_code"),
            func.coalesce(func.sum(holding_expr + retention_expr), 0.0).label("cust_pen_mins"),
            func.coalesce(func.sum(holding_expr * HOLDING_DELAY_COST_RATE_INR_PER_MIN + retention_expr * RETENTION_SLA_PENALTY_RATE_INR_PER_MIN + holding_expr * IDLE_FUEL_WASTE_RATE_INR_PER_MIN), 0.0).label("cust_exp_inr")
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).join(Customer, Dispatch.customer_id == Customer.id, isouter=True)

        if effective_plant != "ALL":
            q_cust = q_cust.where(Plant.code == effective_plant)
        if effective_customer != "ALL":
            q_cust = q_cust.where(Customer.code == effective_customer)

        q_cust = q_cust.group_by(Customer.code).order_by(text("cust_exp_inr DESC")).limit(5)
        res_cust = await session.execute(q_cust)
        cust_risk: List[EntityFinancialRiskItemDTO] = []
        for r in res_cust.fetchall():
            c_code = r.cust_code or "UNASSIGNED"
            cust_risk.append(
                EntityFinancialRiskItemDTO(
                    entity_type="CUSTOMER",
                    entity_code=c_code,
                    entity_name=c_code,
                    penalty_mins=round(float(r.cust_pen_mins), 1),
                    financial_exposure_inr=round(float(r.cust_exp_inr), 2),
                )
            )

        filter_desc = f"Plant: {effective_plant}, Customer: {effective_customer}, Dataset: {effective_dataset}"
        return OperationalFinancialExposureResponseDTO(
            summary=summary_dto,
            breakdown=breakdown_items,
            top_plant_risk=plant_risk,
            top_customer_risk=cust_risk,
            calculation_status="SUCCESS",
            calculation_notes=f"Authoritative financial exposure calculation successful across ₹{total_exposure:,.2f} total risk (Plant: {effective_plant}, Customer: {effective_customer}, Dataset: {effective_dataset}).",
        )
