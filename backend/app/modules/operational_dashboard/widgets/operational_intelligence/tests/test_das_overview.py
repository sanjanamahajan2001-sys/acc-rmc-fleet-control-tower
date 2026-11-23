import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_overview import DASOverviewEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    DASOverviewResponseDTO,
    OperationalIntelligenceStatusEnum,
)

@pytest.mark.asyncio
async def test_das_overview_evaluations():
    """Target SLA = 90.0%, Accurate <= 20.0m, Moderate <= 40.0m and 5-scope reconciliation."""
    assert DASOverviewEngine.TARGET_SLA == 90.0
    assert DASOverviewEngine.ACCURATE_THRESHOLD_MINS == 20.0
    assert DASOverviewEngine.MODERATE_THRESHOLD_MINS == 40.0

    async with AsyncSessionFactory() as session:
        # V-01 Global Scope (ALL / ALL / ALL): 6834 dispatches
        res_v01: DASOverviewResponseDTO = await DASOverviewEngine.evaluate_overview(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "ALL"}
        )
        assert res_v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v01.summary.total_dispatches == 6834
        assert res_v01.summary.accurate_dispatches == 3759
        assert res_v01.summary.das_score == 55.0
        assert res_v01.summary.operational_status == "CRITICAL"
        assert res_v01.buckets.within_20m_count == 3759
        assert (
            res_v01.buckets.within_20m_count
            + res_v01.buckets.range_21_40m_count
            + res_v01.buckets.range_41_60m_count
            + res_v01.buckets.above_60m_count
        ) == res_v01.summary.total_dispatches
        assert (
            res_v01.buckets.within_20m_count
            + res_v01.buckets.moderate_20_40m_count
            + res_v01.buckets.critical_above_40m_count
        ) == res_v01.summary.total_dispatches

        # V-05 Synthetic Scope (ALL / ALL / SYNTHETIC_ONLY): 0 trips | NO_OBSERVATIONS | NEUTRAL
        res_v05: DASOverviewResponseDTO = await DASOverviewEngine.evaluate_overview(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        )
        assert res_v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert res_v05.summary.total_dispatches == 0
        assert res_v05.summary.accurate_dispatches == 0
        assert res_v05.summary.das_score is None
        assert res_v05.summary.operational_status == "NEUTRAL"
        assert res_v05.buckets.within_20m_count == 0
        assert res_v05.buckets.within_20m_pct == 0.0
