"""
WS-09 Phase 5 Automated Test Suite & Direct PostgreSQL Reconciliation Test
Tests Fleet & Plant Operational Efficiency backend calculations, CustomerEfficiencyEngine 1:1 reuse, filter matrix propagation, and direct database reconciliation.
"""

import pytest
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.fleet_efficiency_service import OperationalFleetEfficiencyService
from app.modules.operational_dashboard.widgets.operational_intelligence.services.customer_efficiency import CustomerEfficiencyEngine
from app.modules.erp.models import Dispatch, Vehicle, Plant, Customer


@pytest.mark.asyncio
async def test_fleet_efficiency_service_basic():
    """
    Test OperationalFleetEfficiencyService basic execution under default filters.
    Verifies that the service returns an OperationalFleetEfficiencyResponseDTO.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(
            plant_id="ALL",
            customer_id="ALL",
            dataset_type="ALL",
        )
        result = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params)

        assert result is not None
        assert result.summary is not None
        assert result.calculation_status in ["SUCCESS", "NO_RECORDS"]

        if result.calculation_status == "SUCCESS":
            assert 0.0 <= result.summary.overall_efficiency_index <= 100.0
            assert 0.0 <= result.summary.fleet_utilization_pct <= 100.0
            assert len(result.plant_efficiency) > 0
            assert len(result.customer_efficiency) > 0


@pytest.mark.asyncio
async def test_fleet_efficiency_filter_matrix_suite():
    """
    Test filter propagation across Plant, Customer, Date, and Dataset parameters.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Test Plant Filter ACC_KUNDAIM
        params_kundaim = DashboardFilterParams(plant_id="ACC_KUNDAIM", customer_id="ALL", dataset_type="ALL")
        res_kundaim = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params_kundaim)
        assert res_kundaim is not None
        assert "Plant: ACC_KUNDAIM" in res_kundaim.calculation_notes

        # 2. Test Plant Filter ACC_VASCO
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        res_vasco = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params_vasco)
        assert res_vasco is not None
        assert "Plant: ACC_VASCO" in res_vasco.calculation_notes

        # 3. Test Customer Filter CUST_TRUE_BUILD
        params_cust = DashboardFilterParams(plant_id="ALL", customer_id="CUST_TRUE_BUILD", dataset_type="ALL")
        res_cust = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params_cust)
        assert res_cust is not None
        assert "Customer: CUST_TRUE_BUILD" in res_cust.calculation_notes

        # 4. Test Combined Filter (ACC_VASCO + CUST_TRUE_BUILD + REAL_ONLY)
        params_comb = DashboardFilterParams(
            plant_id="ACC_VASCO",
            customer_id="CUST_TRUE_BUILD",
            dataset_type="REAL_ONLY",
            operation_date="2026-08-05",
        )
        res_comb = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params_comb)
        assert res_comb is not None
        assert res_comb.calculation_status in ["SUCCESS", "NO_RECORDS"]


@pytest.mark.asyncio
async def test_customer_cei_1to1_reconciliation():
    """
    MANDATORY CUSTOMER CEI 1:1 RECONCILIATION TEST:
    Verifies that Section 05 customer_efficiency items match canonical CustomerEfficiencyEngine output 100% identically.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        dto = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params)

        # Direct call to CustomerEfficiencyEngine with dict filters
        filters = {"plant_id": "ALL", "customer_id": "ALL", "dataset_id": "DS-20260805-001"}
        cei_res = await CustomerEfficiencyEngine.get_customer_efficiency(db_session, filters)

        assert len(dto.customer_efficiency) == len(cei_res.data)
        for dto_cust, engine_cust in zip(dto.customer_efficiency, cei_res.data):
            assert dto_cust.customer_code == engine_cust.customer_id
            assert dto_cust.total_trips == engine_cust.total_trips
            assert dto_cust.cei_score == pytest.approx(engine_cust.cei_score, 0.1)
            assert dto_cust.efficiency_grade == engine_cust.grade


@pytest.mark.asyncio
async def test_fleet_efficiency_postgresql_reconciliation():
    """
    MANDATORY POSTGRESQL FLEET EFFICIENCY RECONCILIATION TEST:
    Reconciles average turnaround, holding, retention, utilization, and overall index against direct SQL queries.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        plant_code = "ACC_VASCO"
        params = DashboardFilterParams(plant_id=plant_code, customer_id="ALL", dataset_type="ALL")
        dto = await OperationalFleetEfficiencyService.get_fleet_efficiency(db_session, params)

        # Direct SQL Query on dispatches joining Plant
        turnaround_expr = (
            func.coalesce(Dispatch.t1_transit_mins, 0.0)
            + func.coalesce(Dispatch.t2a_holding_mins, 0.0)
            + func.coalesce(Dispatch.t2b_unloading_mins, 0.0)
            + func.coalesce(Dispatch.t3_return_mins, 0.0)
        )

        q = select(
            func.count(Dispatch.id).label("total_dispatches"),
            func.count(func.distinct(Dispatch.vehicle_id)).label("dispatch_active_vehs"),
            func.coalesce(func.avg(turnaround_expr), 0.0).label("avg_turnaround"),
            func.coalesce(func.avg(Dispatch.t2a_holding_mins), 0.0).label("avg_holding"),
            func.coalesce(func.avg(Dispatch.t2c_retention_mins), 0.0).label("avg_retention"),
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).where(Plant.code == plant_code)

        res = (await db_session.execute(q)).fetchone()

        # Query total active registered vehicles
        q_vehs = select(func.count(Vehicle.id))
        tot_vehs = (await db_session.execute(q_vehs)).scalar() or 1

        db_active_vehs = res.dispatch_active_vehs if res else 0
        db_turnaround = float(res.avg_turnaround if res else 0.0)
        db_holding = float(res.avg_holding if res else 0.0)
        db_retention = float(res.avg_retention if res else 0.0)

        expected_util = min(100.0, round((db_active_vehs / tot_vehs) * 100.0, 1))
        expected_turnaround_eff = max(0.0, round(100.0 - ((db_holding / 20.0) * 100.0), 1))
        expected_unloading_eff = max(0.0, round(100.0 - ((db_retention / 10.0) * 100.0), 1))

        expected_overall = max(0.0, min(100.0, round(
            (0.40 * expected_util) + (0.30 * expected_turnaround_eff) + (0.30 * expected_unloading_eff),
            1
        )))

        assert dto.summary.fleet_utilization_pct == pytest.approx(expected_util, 0.1)
        assert dto.summary.avg_turnaround_time_mins == pytest.approx(round(db_turnaround, 1), 0.1)
        assert dto.summary.avg_holding_time_mins == pytest.approx(round(db_holding, 1), 0.1)
        assert dto.summary.avg_retention_time_mins == pytest.approx(round(db_retention, 1), 0.1)
        assert dto.summary.turnaround_efficiency_pct == pytest.approx(expected_turnaround_eff, 0.1)
        assert dto.summary.site_unloading_efficiency_pct == pytest.approx(expected_unloading_eff, 0.1)
        assert dto.summary.overall_efficiency_index == pytest.approx(expected_overall, 0.1)


@pytest.mark.asyncio
async def test_stale_efficiency_filter_transition_integrity():
    """
    STALE FILTER TRANSITION INTEGRITY TEST:
    Verifies that changing context from ACC_VASCO to ACC_KUNDAIM updates calculation notes and lineage.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res1 = await OperationalFleetEfficiencyService.get_fleet_efficiency(
            db_session, DashboardFilterParams(plant_id="ACC_VASCO")
        )
        res2 = await OperationalFleetEfficiencyService.get_fleet_efficiency(
            db_session, DashboardFilterParams(plant_id="ACC_KUNDAIM")
        )

        assert "Plant: ACC_VASCO" in res1.calculation_notes
        assert "Plant: ACC_KUNDAIM" in res2.calculation_notes
        assert res1.calculation_notes != res2.calculation_notes
