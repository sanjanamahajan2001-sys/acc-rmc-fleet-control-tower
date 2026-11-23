"""
WS-09 Phase 6.4 Automated Pytest Suite & Independent PostgreSQL Reconciliation Test
Tests Cost & Exposure Intelligence backend calculations, Phase 4 financial authority reconciliation,
filter matrix propagation, high-cost operations pagination & risk levels, plant/customer risk aggregation,
prediction provenance integrity, and cross-section financial reconciliation vs Section 04.
"""

import math
import pytest
from sqlalchemy import select, func, text, or_
from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.cost_exposure_service import (
    OperationalCostExposureService,
    HOLDING_DELAY_COST_RATE_INR_PER_MIN,
    RETENTION_SLA_PENALTY_RATE_INR_PER_MIN,
    IDLE_FUEL_WASTE_RATE_INR_PER_MIN,
)
from app.modules.operational_intelligence.services.financial_exposure_service import OperationalFinancialExposureService
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle


@pytest.mark.asyncio
async def test_cost_exposure_service_basic():
    """
    Test OperationalCostExposureService basic execution under default filters.
    Verifies that the service returns a valid OperationalCostExposureResponseDTO.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(
            plant_id="ALL",
            customer_id="ALL",
            dataset_type="ALL",
        )
        result = await OperationalCostExposureService.get_cost_exposure(db_session, params, page=1, page_size=10)

        assert result is not None
        assert result.summary is not None
        assert result.calculation_status in ["SUCCESS", "NO_RECORDS"]
        assert result.prediction_status == "NOT_CONFIGURED"
        assert result.provenance.is_model_configured is False
        assert result.summary.predicted_cost_exposure_inr is None

        if result.calculation_status == "SUCCESS":
            assert result.summary.realized_cost_exposure_inr >= 0.0
            assert result.summary.holding_penalty_cost_inr >= 0.0
            assert result.summary.retention_sla_penalty_inr >= 0.0
            assert result.summary.idle_fuel_waste_inr >= 0.0
            assert result.summary.high_cost_operations_count >= 0
            assert len(result.plant_cost_risk) > 0
            assert len(result.customer_cost_risk) > 0

            # Verify summary invariant: total = holding + retention + idle fuel
            expected_total = round(
                result.summary.holding_penalty_cost_inr
                + result.summary.retention_sla_penalty_inr
                + result.summary.idle_fuel_waste_inr,
                2,
            )
            assert result.summary.realized_cost_exposure_inr == pytest.approx(expected_total, 0.01)


@pytest.mark.asyncio
async def test_cost_exposure_filter_matrix_suite():
    """
    Test filter matrix propagation across Plant, Customer, Date, and Dataset parameters.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Test Plant Filter ACC_KUNDAIM
        params_kundaim = DashboardFilterParams(plant_id="ACC_KUNDAIM", customer_id="ALL", dataset_type="ALL")
        res_kundaim = await OperationalCostExposureService.get_cost_exposure(db_session, params_kundaim)
        assert res_kundaim is not None
        assert "Plant: ACC_KUNDAIM" in res_kundaim.calculation_notes

        # 2. Test Plant Filter ACC_VASCO
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        res_vasco = await OperationalCostExposureService.get_cost_exposure(db_session, params_vasco)
        assert res_vasco is not None
        assert "Plant: ACC_VASCO" in res_vasco.calculation_notes

        # 3. Test Customer Filter CUST_TRUE_BUILD
        params_cust = DashboardFilterParams(plant_id="ALL", customer_id="CUST_TRUE_BUILD", dataset_type="ALL")
        res_cust = await OperationalCostExposureService.get_cost_exposure(db_session, params_cust)
        assert res_cust is not None
        assert "Customer: CUST_TRUE_BUILD" in res_cust.calculation_notes

        # 4. Test Combined Filter (ACC_VASCO + CUST_TRUE_BUILD + REAL_ONLY)
        params_comb = DashboardFilterParams(
            plant_id="ACC_VASCO",
            customer_id="CUST_TRUE_BUILD",
            dataset_type="REAL_ONLY",
            operation_date="2026-08-05",
        )
        res_comb = await OperationalCostExposureService.get_cost_exposure(db_session, params_comb)
        assert res_comb is not None
        assert res_comb.calculation_status in ["SUCCESS", "NO_RECORDS"]


@pytest.mark.asyncio
async def test_cost_exposure_postgresql_reconciliation():
    """
    MANDATORY INDEPENDENT POSTGRESQL FINANCIAL RECONCILIATION TEST:
    Executes raw SQL against dispatches and recalculates financial exposure components independently.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        plant_code = "ACC_VASCO"
        params = DashboardFilterParams(plant_id=plant_code, customer_id="ALL", dataset_type="ALL")
        dto = await OperationalCostExposureService.get_cost_exposure(db_session, params)

        # Independent SQL Query on dispatches joining Plant
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
        expected_idle_fuel_cost = round(db_holding_mins * 15.0, 2)
        expected_total_exposure = round(expected_holding_cost + expected_retention_cost + expected_idle_fuel_cost, 2)

        assert dto.summary.holding_penalty_cost_inr == pytest.approx(expected_holding_cost, 0.01)
        assert dto.summary.retention_sla_penalty_inr == pytest.approx(expected_retention_cost, 0.01)
        assert dto.summary.idle_fuel_waste_inr == pytest.approx(expected_idle_fuel_cost, 0.01)
        assert dto.summary.realized_cost_exposure_inr == pytest.approx(expected_total_exposure, 0.01)


@pytest.mark.asyncio
async def test_high_cost_operations_reconciliation_and_risk_levels():
    """
    INDEPENDENT HIGH-COST OPERATIONS & RISK LEVEL RECONCILIATION TEST:
    Verifies qualifying high-cost dispatches, pagination, risk classification, and deterministic ordering.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        page_size = 5
        dto_page1 = await OperationalCostExposureService.get_cost_exposure(db_session, params, page=1, page_size=page_size)
        dto_page2 = await OperationalCostExposureService.get_cost_exposure(db_session, params, page=2, page_size=page_size)

        holding_expr = func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)
        retention_expr = func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)

        # Count total high-cost operations independently
        q_count = select(func.count(Dispatch.id)).where(or_(holding_expr > 0.0, retention_expr > 0.0))
        total_qualifying = (await db_session.execute(q_count)).scalar() or 0

        assert dto_page1.high_cost_operations.total_items == total_qualifying
        expected_pages = math.ceil(total_qualifying / page_size) if total_qualifying > 0 else 0
        assert dto_page1.high_cost_operations.total_pages == expected_pages

        # Verify page 1 items risk level classification and deterministic ordering
        if dto_page1.high_cost_operations.total_items > 0:
            assert len(dto_page1.high_cost_operations.items) == min(page_size, total_qualifying)
            prev_exp = float("inf")
            for item in dto_page1.high_cost_operations.items:
                # Ordering check
                assert item.total_exposure_inr <= prev_exp
                prev_exp = item.total_exposure_inr

                # Risk level check
                if item.total_exposure_inr >= 1000.0:
                    assert item.risk_level == "Critical"
                elif item.total_exposure_inr >= 500.0:
                    assert item.risk_level == "High"
                else:
                    assert item.risk_level == "Moderate"

            # Page 2 no duplicate IDs check vs Page 1
            page1_ids = {item.dispatch_id for item in dto_page1.high_cost_operations.items}
            page2_ids = {item.dispatch_id for item in dto_page2.high_cost_operations.items}
            assert len(page1_ids.intersection(page2_ids)) == 0


@pytest.mark.asyncio
async def test_plant_and_customer_risk_reconciliation():
    """
    PLANT & CUSTOMER RISK AGGREGATION RECONCILIATION TEST:
    Verifies that plant and customer sum exposures match total realized exposure 100%.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        dto = await OperationalCostExposureService.get_cost_exposure(db_session, params)

        if dto.summary.realized_cost_exposure_inr > 0:
            sum_plant_exposure = round(sum(p.total_exposure_inr for p in dto.plant_cost_risk), 2)
            sum_cust_exposure = round(sum(c.total_exposure_inr for c in dto.customer_cost_risk), 2)

            assert sum_plant_exposure == pytest.approx(dto.summary.realized_cost_exposure_inr, 0.01)
            assert sum_cust_exposure == pytest.approx(dto.summary.realized_cost_exposure_inr, 0.01)

            # Percentage sum verification (~100%)
            sum_plant_pct = sum(p.exposure_percentage for p in dto.plant_cost_risk)
            sum_cust_pct = sum(c.exposure_percentage for c in dto.customer_cost_risk)

            assert sum_plant_pct == pytest.approx(100.0, 0.5)
            assert sum_cust_pct == pytest.approx(100.0, 0.5)


@pytest.mark.asyncio
async def test_stale_cost_exposure_filter_transition_integrity():
    """
    STALE FILTER TRANSITION INTEGRITY TEST:
    Verifies that changing context from ACC_VASCO to ACC_KUNDAIM updates calculation notes and lineage.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res1 = await OperationalCostExposureService.get_cost_exposure(
            db_session, DashboardFilterParams(plant_id="ACC_VASCO")
        )
        res2 = await OperationalCostExposureService.get_cost_exposure(
            db_session, DashboardFilterParams(plant_id="ACC_KUNDAIM")
        )

        assert "Plant: ACC_VASCO" in res1.calculation_notes
        assert "Plant: ACC_KUNDAIM" in res2.calculation_notes
        assert res1.calculation_notes != res2.calculation_notes


@pytest.mark.asyncio
async def test_prediction_provenance_and_status_separation():
    """
    PREDICTION PROVENANCE & STATUS SEPARATION TEST:
    Verifies truthful representation of NOT_CONFIGURED prediction engine while calculation_status is SUCCESS.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        dto = await OperationalCostExposureService.get_cost_exposure(db_session, params)

        assert dto.calculation_status in ["SUCCESS", "NO_RECORDS"]
        assert dto.prediction_status == "NOT_CONFIGURED"
        assert dto.provenance.is_model_configured is False
        assert dto.summary.predicted_cost_exposure_inr is None
        assert dto.provenance.model_name is None
        assert dto.provenance.model_version is None
        assert dto.provenance.prediction_snapshot_id is None
        assert dto.provenance.prediction_timestamp is None
        assert dto.provenance.confidence_score is None


@pytest.mark.asyncio
async def test_cross_section_reconciliation_sec04_vs_sec06():
    """
    MANDATORY CROSS-SECTION RECONCILIATION TEST:
    Verifies that Section 04 Financial Loss Total Exposure matches Section 06 Realized Cost Exposure 100% identically.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        for plant_code in ["ALL", "ACC_VASCO", "ACC_KUNDAIM", "ACC_DHARGA", "ACC_NESSAI"]:
            params = DashboardFilterParams(plant_id=plant_code, customer_id="ALL", dataset_type="ALL")
            dto_sec04 = await OperationalFinancialExposureService.get_financial_exposure(db_session, params)
            dto_sec06 = await OperationalCostExposureService.get_cost_exposure(db_session, params)

            assert dto_sec06.summary.realized_cost_exposure_inr == pytest.approx(dto_sec04.summary.total_financial_exposure_inr, 0.01)
            assert dto_sec06.summary.holding_penalty_cost_inr == pytest.approx(dto_sec04.summary.holding_delay_cost_inr, 0.01)
            assert dto_sec06.summary.retention_sla_penalty_inr == pytest.approx(dto_sec04.summary.retention_sla_penalty_inr, 0.01)
            assert dto_sec06.summary.idle_fuel_waste_inr == pytest.approx(dto_sec04.summary.idle_fuel_waste_inr, 0.01)
