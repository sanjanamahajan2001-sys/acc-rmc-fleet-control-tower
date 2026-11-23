"""
WS-09 Phase 1 Automated Test Suite & Direct PostgreSQL Reconciliation Test
Tests Operational Health backend calculations, filter matrix propagation, and database reconciliation.
"""

import pytest
from sqlalchemy import select, func
from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.health_service import OperationalHealthService
from app.modules.erp.models import Dispatch, Plant, Customer


@pytest.mark.asyncio
async def test_operational_health_service_basic():
    """
    Test OperationalHealthService basic execution under default filters.
    Verifies that the service returns an OperationalHealthResponseDTO with provenance.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(
            plant_id="ALL",
            customer_id="ALL",
            dataset_type="ALL",
        )
        result = await OperationalHealthService.get_operational_health(db_session, params)

        assert result is not None
        assert result.freshness is not None
        assert result.calculation_status in ["SUCCESS", "NO_RECORDS"]
        
        if result.calculation_status == "SUCCESS":
            assert len(result.metrics) == 5
            for m in result.metrics:
                assert m.provenance_table is not None
                assert m.provenance_formula is not None


@pytest.mark.asyncio
async def test_operational_health_filter_matrix_suite():
    """
    Test filter propagation across Plant, Customer, Date, and Dataset Type parameters.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Test Plant Filter ACC_VASCO
        params_plant = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        res_plant = await OperationalHealthService.get_operational_health(db_session, params_plant)
        assert res_plant is not None
        assert res_plant.calculation_status in ["SUCCESS", "NO_RECORDS"]

        # 2. Test Customer Filter CUST_TRUE_BUILD
        params_cust = DashboardFilterParams(plant_id="ALL", customer_id="CUST_TRUE_BUILD", dataset_type="ALL")
        res_cust = await OperationalHealthService.get_operational_health(db_session, params_cust)
        assert res_cust is not None
        assert res_cust.calculation_status in ["SUCCESS", "NO_RECORDS"]

        # 3. Test Combined Filter (ACC_VASCO + CUST_TRUE_BUILD + REAL_ONLY)
        params_comb = DashboardFilterParams(
            plant_id="ACC_VASCO",
            customer_id="CUST_TRUE_BUILD",
            dataset_type="REAL_ONLY",
            operation_date="2026-08-05",
        )
        res_comb = await OperationalHealthService.get_operational_health(db_session, params_comb)
        assert res_comb is not None
        assert res_comb.calculation_status in ["SUCCESS", "NO_RECORDS"]
        assert res_comb.freshness.operational_date == "2026-08-05"


@pytest.mark.asyncio
async def test_postgresql_direct_reconciliation():
    """
    MANDATORY RECONCILIATION TEST:
    Verifies that total dispatches returned by the API matches direct SQL count from `dispatches` table
    under both overall (ALL) and filtered (ACC_VASCO) contexts.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Overall Context Reconciliation
        params_all = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        dto_all = await OperationalHealthService.get_operational_health(db_session, params_all)

        query_all = select(func.count(Dispatch.id)).where(Dispatch.is_deleted == False)
        db_res_all = await db_session.execute(query_all)
        direct_db_count_all = db_res_all.scalar_one_or_none() or 0

        assert dto_all.freshness.total_dispatches == direct_db_count_all

        # 2. Filtered Plant Context Reconciliation (ACC_VASCO)
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        dto_vasco = await OperationalHealthService.get_operational_health(db_session, params_vasco)

        plant_stmt = select(Plant.id).where(Plant.code == "ACC_VASCO")
        vasco_id = (await db_session.execute(plant_stmt)).scalar()

        query_vasco = select(func.count(Dispatch.id)).where(Dispatch.is_deleted == False, Dispatch.plant_id == vasco_id)
        db_res_vasco = await db_session.execute(query_vasco)
        direct_db_count_vasco = db_res_vasco.scalar_one_or_none() or 0

        assert dto_vasco.freshness.total_dispatches == direct_db_count_vasco
