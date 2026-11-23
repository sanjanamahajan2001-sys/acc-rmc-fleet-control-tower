import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.holding_retention import HoldingRetentionEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    HoldingRetentionResponseDTO,
    OperationalIntelligenceStatusEnum,
)

@pytest.mark.asyncio
async def test_ws_03_3_phase3v_vertical_slice_end_to_end():
    """WS-03.3 Phase 3V End-to-End Vertical Slice Verification across 5 mandatory scopes."""
    async with AsyncSessionFactory() as session:
        # V-01 Global Scope (ALL / ALL / REAL_ONLY)
        res_v01: HoldingRetentionResponseDTO = await HoldingRetentionEngine.evaluate_overview(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        )
        assert res_v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v01.summary.total_dispatches == 3532
        assert res_v01.summary.total_holding_penalty_mins == 42142.0
        assert res_v01.summary.total_retention_penalty_mins == 14490.0
        assert res_v01.summary.total_lost_hours == 943.9
        assert len(res_v01.data) == 24
        assert res_v01.data[0].hour_label == "00:00"
        assert res_v01.data[23].hour_label == "23:00"

        # V-02 Dharga Scope (ACC_DHARGA / ALL / REAL_ONLY)
        res_v02: HoldingRetentionResponseDTO = await HoldingRetentionEngine.evaluate_overview(
            session, {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        )
        assert res_v02.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v02.summary.total_dispatches == 978
        assert res_v02.summary.total_holding_penalty_mins == 13602.0
        assert res_v02.summary.total_retention_penalty_mins == 5928.0
        assert res_v02.summary.total_lost_hours == 325.5
        assert len(res_v02.data) == 24

        # V-03 Vasco Scope (ACC_VASCO / ALL / REAL_ONLY)
        res_v03: HoldingRetentionResponseDTO = await HoldingRetentionEngine.evaluate_overview(
            session, {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        )
        assert res_v03.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v03.summary.total_dispatches == 1174
        assert res_v03.summary.total_holding_penalty_mins == 10221.0
        assert res_v03.summary.total_retention_penalty_mins == 3519.0
        assert res_v03.summary.total_lost_hours == 229.0
        assert len(res_v03.data) == 24

        # V-04 Customer Scope (ACC_KUNDAIM / CUST_AARA_HOTELS)
        res_v04: HoldingRetentionResponseDTO = await HoldingRetentionEngine.evaluate_overview(
            session, {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}
        )
        assert res_v04.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v04.summary.total_dispatches == 3
        assert res_v04.summary.total_holding_penalty_mins == 11.0
        assert res_v04.summary.total_retention_penalty_mins == 0.0
        assert res_v04.summary.total_lost_hours == 0.2
        assert len(res_v04.data) == 24

        # V-05 Synthetic Scope (ALL / ALL / SYNTHETIC_ONLY)
        res_v05: HoldingRetentionResponseDTO = await HoldingRetentionEngine.evaluate_overview(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        )
        assert res_v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert res_v05.summary.total_dispatches == 0
        assert res_v05.summary.total_holding_penalty_mins == 0.0
        assert res_v05.summary.total_retention_penalty_mins == 0.0
        assert res_v05.summary.total_lost_hours == 0.0
        assert res_v05.data == []
