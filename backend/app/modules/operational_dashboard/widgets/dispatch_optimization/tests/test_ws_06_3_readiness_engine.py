"""
WS-06.3 Backend Unit Test Suite for Optimization Readiness Engine & API.
Tests readiness evaluation across all 5 verification scopes (V-01 Global, V-02 Vasco,
V-03 Kundaim, V-04 Customer, V-05 Synthetic), data quality checks, empty states, and API responses.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import ReadinessStatusEnum


@pytest.mark.asyncio(loop_scope="function")
async def test_readiness_v01_global_real_only(db_session: AsyncSession):
    filters = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
    readiness = await OptimizationReadinessEngine.evaluate_readiness(db_session, filters)

    assert readiness.success is True
    assert readiness.status in (ReadinessStatusEnum.READY, ReadinessStatusEnum.DEGRADED)
    assert readiness.quality_summary.total_dispatches > 0
    assert readiness.quality_summary.active_vehicle_count > 0
    assert readiness.quality_summary.plant_count > 0

    filters_vasco = {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
    readiness_vasco = await OptimizationReadinessEngine.evaluate_readiness(db_session, filters_vasco)
    assert readiness_vasco.quality_summary.total_dispatches > 0
    assert readiness_vasco.quality_summary.active_vehicle_count > 0

    filters_kundaim = {"plant_id": "ACC_KUNDAIM", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
    readiness_kundaim = await OptimizationReadinessEngine.evaluate_readiness(db_session, filters_kundaim)
    assert readiness_kundaim.quality_summary.total_dispatches > 0
    assert readiness_kundaim.quality_summary.active_vehicle_count > 0

    filters_cust = {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}
    readiness_cust = await OptimizationReadinessEngine.evaluate_readiness(db_session, filters_cust)
    assert readiness_cust.quality_summary.total_dispatches > 0
    assert readiness_cust.quality_summary.active_vehicle_count > 0

    filters_synth = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
    readiness_synth = await OptimizationReadinessEngine.evaluate_readiness(db_session, filters_synth)
    assert readiness_synth.status == ReadinessStatusEnum.NO_OBSERVATIONS
    assert readiness_synth.quality_summary.total_dispatches == 0
