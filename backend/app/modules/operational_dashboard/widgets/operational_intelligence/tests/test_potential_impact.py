import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.potential_impact import PotentialImpactEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    PotentialImpactResponseDTO,
    OperationalIntelligenceStatusEnum,
)

@pytest.mark.asyncio
async def test_01_potential_impact_constants():
    """Verify approved contract parameters: 20% reduction & 0.8 trips/hr factor."""
    assert PotentialImpactEngine.REDUCTION_PCT == 20.0
    assert PotentialImpactEngine.TRIPS_PER_HOUR_FACTOR == 0.8

@pytest.mark.asyncio
async def test_02_five_scope_reconciliation():
    """Reconciles 5 mandatory filter scopes against PostgreSQL database baseline."""
    async with AsyncSessionFactory() as session:
        # V-01 Global Scope (ALL / ALL / REAL_ONLY): 3532 trips | 140.5h holding | 112 trips | 48.3h retention | 39 trips | 188.8h total | 151 trips
        res_v01: PotentialImpactResponseDTO = await PotentialImpactEngine.evaluate_impact(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        )
        assert res_v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v01.data["holding_impact"]["saved_hours_total"] == 140.5
        assert res_v01.data["holding_impact"]["trips_unlocked"] == 112
        assert res_v01.data["retention_impact"]["saved_hours_total"] == 48.3
        assert res_v01.data["retention_impact"]["trips_unlocked"] == 39
        assert res_v01.data["total_impact"]["saved_hours_total"] == 188.8
        assert res_v01.data["total_impact"]["total_trips_unlocked"] == 151
        assert res_v01.data["holding_impact"]["trips_unlocked"] + res_v01.data["retention_impact"]["trips_unlocked"] == res_v01.data["total_impact"]["total_trips_unlocked"]

        # V-02 Dharga Scope (ACC_DHARGA / ALL / REAL_ONLY): 45.3h holding (36) | 19.8h retention (16) | 65.1h total (52)
        res_v02: PotentialImpactResponseDTO = await PotentialImpactEngine.evaluate_impact(
            session, {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        )
        assert res_v02.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v02.data["holding_impact"]["saved_hours_total"] == 45.3
        assert res_v02.data["holding_impact"]["trips_unlocked"] == 36
        assert res_v02.data["retention_impact"]["saved_hours_total"] == 19.8
        assert res_v02.data["retention_impact"]["trips_unlocked"] == 16
        assert res_v02.data["total_impact"]["saved_hours_total"] == 65.1
        assert res_v02.data["total_impact"]["total_trips_unlocked"] == 52

        # V-03 Vasco Scope (ACC_VASCO / ALL / REAL_ONLY): 34.1h holding (27) | 11.7h retention (9) | 45.8h total (36)
        res_v03: PotentialImpactResponseDTO = await PotentialImpactEngine.evaluate_impact(
            session, {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        )
        assert res_v03.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v03.data["holding_impact"]["saved_hours_total"] == 34.1
        assert res_v03.data["holding_impact"]["trips_unlocked"] == 27
        assert res_v03.data["retention_impact"]["saved_hours_total"] == 11.7
        assert res_v03.data["retention_impact"]["trips_unlocked"] == 9
        assert res_v03.data["total_impact"]["saved_hours_total"] == 45.8
        assert res_v03.data["total_impact"]["total_trips_unlocked"] == 36

        # V-04 Customer Scope (ACC_KUNDAIM / CUST_AARA_HOTELS / REAL_ONLY): 0.0h holding (0) | 0.0h retention (0) | 0.0h total (0)
        res_v04: PotentialImpactResponseDTO = await PotentialImpactEngine.evaluate_impact(
            session, {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}
        )
        assert res_v04.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v04.data["holding_impact"]["saved_hours_total"] == 0.0
        assert res_v04.data["holding_impact"]["trips_unlocked"] == 0
        assert res_v04.data["retention_impact"]["saved_hours_total"] == 0.0
        assert res_v04.data["retention_impact"]["trips_unlocked"] == 0
        assert res_v04.data["total_impact"]["saved_hours_total"] == 0.0
        assert res_v04.data["total_impact"]["total_trips_unlocked"] == 0

        # V-05 Synthetic Scope (ALL / ALL / SYNTHETIC_ONLY): 0 dispatches -> NO_OBSERVATIONS
        res_v05: PotentialImpactResponseDTO = await PotentialImpactEngine.evaluate_impact(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        )
        assert res_v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert res_v05.data["holding_impact"]["saved_hours_total"] == 0.0
        assert res_v05.data["holding_impact"]["trips_unlocked"] == 0
        assert res_v05.data["retention_impact"]["saved_hours_total"] == 0.0
        assert res_v05.data["retention_impact"]["trips_unlocked"] == 0
        assert res_v05.data["total_impact"]["saved_hours_total"] == 0.0
        assert res_v05.data["total_impact"]["total_trips_unlocked"] == 0
