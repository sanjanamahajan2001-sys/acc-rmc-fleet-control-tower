"""
WS-09 Phase 4 Automated Test Suite & Direct PostgreSQL Reconciliation Test
Tests Financial Loss & SLA Risk Exposure backend calculations, filter matrix propagation, and direct database reconciliation.
"""

import pytest
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.financial_exposure_service import OperationalFinancialExposureService
from app.modules.erp.models import Dispatch, Plant, Customer


@pytest.mark.asyncio
async def test_financial_exposure_service_basic():
    """
    Test OperationalFinancialExposureService basic execution under default filters.
    Verifies that the service returns an OperationalFinancialExposureResponseDTO.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(
            plant_id="ALL",
            customer_id="ALL",
            dataset_type="ALL",
        )
        result = await OperationalFinancialExposureService.get_financial_exposure(db_session, params)

        assert result is not None
        assert result.summary is not None
        assert result.calculation_status in ["SUCCESS", "NO_RECORDS"]

        if result.calculation_status == "SUCCESS":
            assert result.summary.total_financial_exposure_inr >= 0.0
            assert result.summary.holding_delay_cost_inr + result.summary.retention_sla_penalty_inr + result.summary.idle_fuel_waste_inr == pytest.approx(result.summary.total_financial_exposure_inr, 0.01)
            assert len(result.breakdown) == 3


@pytest.mark.asyncio
async def test_financial_exposure_filter_matrix_suite():
    """
    Test filter propagation across Plant, Customer, Date, and Dataset parameters.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Test Plant Filter ACC_KUNDAIM
        params_kundaim = DashboardFilterParams(plant_id="ACC_KUNDAIM", customer_id="ALL", dataset_type="ALL")
        res_kundaim = await OperationalFinancialExposureService.get_financial_exposure(db_session, params_kundaim)
        assert res_kundaim is not None
        assert "Plant: ACC_KUNDAIM" in res_kundaim.calculation_notes

        # 2. Test Plant Filter ACC_VASCO
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        res_vasco = await OperationalFinancialExposureService.get_financial_exposure(db_session, params_vasco)
        assert res_vasco is not None
        assert "Plant: ACC_VASCO" in res_vasco.calculation_notes

        # 3. Test Customer Filter CUST_TRUE_BUILD
        params_cust = DashboardFilterParams(plant_id="ALL", customer_id="CUST_TRUE_BUILD", dataset_type="ALL")
        res_cust = await OperationalFinancialExposureService.get_financial_exposure(db_session, params_cust)
        assert res_cust is not None
        assert "Customer: CUST_TRUE_BUILD" in res_cust.calculation_notes

        # 4. Test Combined Filter (ACC_VASCO + CUST_TRUE_BUILD + REAL_ONLY)
        params_comb = DashboardFilterParams(
            plant_id="ACC_VASCO",
            customer_id="CUST_TRUE_BUILD",
            dataset_type="REAL_ONLY",
            operation_date="2026-08-05",
        )
        res_comb = await OperationalFinancialExposureService.get_financial_exposure(db_session, params_comb)
        assert res_comb is not None
        assert res_comb.calculation_status in ["SUCCESS", "NO_RECORDS"]


@pytest.mark.asyncio
async def test_financial_exposure_postgresql_reconciliation():
    """
    MANDATORY POSTGRESQL FINANCIAL RECONCILIATION TEST:
    Verifies that holding_delay_cost_inr, retention_sla_penalty_inr, and total_financial_exposure_inr
    match direct SQL queries on `dispatches` table under identical filter predicates.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        plant_code = "ACC_VASCO"
        params = DashboardFilterParams(plant_id=plant_code, customer_id="ALL", dataset_type="ALL")
        dto = await OperationalFinancialExposureService.get_financial_exposure(db_session, params)

        # Direct SQL Query on dispatches joining Plant
        holding_expr = func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)
        retention_expr = func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)

        q = select(
            func.coalesce(func.sum(holding_expr), 0.0).label("holding_mins"),
            func.coalesce(func.sum(retention_expr), 0.0).label("retention_mins"),
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).where(Plant.code == plant_code)

        res = (await db_session.execute(q)).fetchone()

        db_holding_mins = float(res.holding_mins if res else 0.0)
        db_retention_mins = float(res.retention_mins if res else 0.0)

        expected_holding_cost = round(db_holding_mins * 25.0, 2)
        expected_retention_cost = round(db_retention_mins * 35.0, 2)
        expected_idle_cost = round(db_holding_mins * 15.0, 2)
        expected_total = round(expected_holding_cost + expected_retention_cost + expected_idle_cost, 2)

        assert dto.summary.holding_delay_cost_inr == pytest.approx(expected_holding_cost, 0.01)
        assert dto.summary.retention_sla_penalty_inr == pytest.approx(expected_retention_cost, 0.01)
        assert dto.summary.idle_fuel_waste_inr == pytest.approx(expected_idle_cost, 0.01)
        assert dto.summary.total_financial_exposure_inr == pytest.approx(expected_total, 0.01)


@pytest.mark.asyncio
async def test_stale_financial_filter_transition_integrity():
    """
    STALE FILTER TRANSITION INTEGRITY TEST:
    Verifies that changing context from ACC_VASCO to ACC_KUNDAIM updates calculation notes and lineage.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res1 = await OperationalFinancialExposureService.get_financial_exposure(
            db_session, DashboardFilterParams(plant_id="ACC_VASCO")
        )
        res2 = await OperationalFinancialExposureService.get_financial_exposure(
            db_session, DashboardFilterParams(plant_id="ACC_KUNDAIM")
        )

        assert "Plant: ACC_VASCO" in res1.calculation_notes
        assert "Plant: ACC_KUNDAIM" in res2.calculation_notes
        assert res1.calculation_notes != res2.calculation_notes
