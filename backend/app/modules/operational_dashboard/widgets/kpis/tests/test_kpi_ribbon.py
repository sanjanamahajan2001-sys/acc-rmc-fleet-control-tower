import pytest
import pytest_asyncio
import asyncio
from datetime import time
from uuid import uuid4

from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPIRibbonResponseDTO,
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.repository import (
    DPIObservation,
    KPIRepository,
    DispatchAccuracyMetrics,
    SWIMetrics,
    FUIMetrics,
)
from app.modules.operational_dashboard.widgets.kpis.services.dispatch_accuracy import DispatchAccuracyEngine
from app.modules.operational_dashboard.widgets.kpis.services.swi import SWIEngine
from app.modules.operational_dashboard.widgets.kpis.services.dpi import DPIEngine
from app.modules.operational_dashboard.widgets.kpis.services.fui import FUIEngine
from app.modules.operational_dashboard.widgets.kpis.services.total_dispatches import TotalDispatchesEngine
from app.modules.operational_dashboard.widgets.kpis.orchestration_service import ExecutiveKPIService


def test_kpi_dto_schema_contracts():
    """Verifies Pydantic v2 DTO schema validation and enum availability fields."""
    card = KPICardItemDTO(
        key="accuracy",
        label="Dispatch Accuracy",
        current_value=None,
        unit="%",
        target=90.0,
        variance=None,
        status=KPIStatusEnum.NEUTRAL,
        availability=AvailabilityEnum.AVAILABLE,
    )
    assert card.current_value is None
    assert card.availability == AvailabilityEnum.AVAILABLE
    assert card.status == KPIStatusEnum.NEUTRAL


def test_volume_source_unavailable_contract():
    """Verifies volume availability is SOURCE_UNAVAILABLE when volume multiplier is omitted and total_volume_m3 is None."""
    total_card = KPICardItemDTO(
        key="total_dispatches",
        label="Total Dispatches",
        current_value=3532.0,
        unit="Trips",
        total_volume_m3=None,
        status=KPIStatusEnum.NEUTRAL,
        availability=AvailabilityEnum.AVAILABLE,
    )
    assert total_card.total_volume_m3 is None
    assert total_card.current_value == 3532.0


def test_dpi_observation_contract():
    """Verifies DPIObservation data structure supports row-level sorting fields."""
    obs = DPIObservation(
        dispatch_id=None,
        customer_id=None,
        time_out=None,
        t1_transit_mins=None,
        t2b_unloading_mins=None,
    )
    assert obs.dispatch_id is None
    assert obs.t1_transit_mins is None


# === WS-03.1 PHASE 2 DISPATCH ACCURACY ENGINE UNIT TESTS ===

def test_dispatch_accuracy_basic_optimal():
    """TEST 1: 10 dispatches, 9 holding <= 20, 1 holding > 20 -> 90.0% OPTIMAL."""
    metrics = DispatchAccuracyMetrics(accurate_count=9, total_count=10)
    dto = DispatchAccuracyEngine().calculate(metrics)
    assert dto.current_value == 90.0
    assert dto.status == KPIStatusEnum.OPTIMAL
    assert dto.variance == 0.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_dispatch_accuracy_warning_threshold():
    """TEST 2: 10 dispatches, 8 accurate, 2 inaccurate -> 80.0% WARNING."""
    metrics = DispatchAccuracyMetrics(accurate_count=8, total_count=10)
    dto = DispatchAccuracyEngine().calculate(metrics)
    assert dto.current_value == 80.0
    assert dto.status == KPIStatusEnum.WARNING
    assert dto.variance == -10.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_dispatch_accuracy_critical_threshold():
    """TEST 3: 10 dispatches, 7 accurate, 3 inaccurate -> 70.0% CRITICAL."""
    metrics = DispatchAccuracyMetrics(accurate_count=7, total_count=10)
    dto = DispatchAccuracyEngine().calculate(metrics)
    assert dto.current_value == 70.0
    assert dto.status == KPIStatusEnum.CRITICAL
    assert dto.variance == -20.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_dispatch_accuracy_zero_observations():
    """TEST 6: Zero observations -> current_value = None, availability = NO_OBSERVATIONS, status = NEUTRAL."""
    metrics = DispatchAccuracyMetrics(accurate_count=0, total_count=0)
    dto = DispatchAccuracyEngine().calculate(metrics)
    assert dto.current_value is None
    assert dto.variance is None
    assert dto.status == KPIStatusEnum.NEUTRAL
    assert dto.availability == AvailabilityEnum.NO_OBSERVATIONS


def test_dispatch_accuracy_none_observations():
    """TEST 7: None observations -> current_value = None, availability = NO_OBSERVATIONS."""
    dto = DispatchAccuracyEngine().calculate(None)
    assert dto.current_value is None
    assert dto.availability == AvailabilityEnum.NO_OBSERVATIONS


# === WS-03.1 PHASE 3 SITE WAITING INDEX (SWI) ENGINE UNIT TESTS ===

def test_swi_optimal_threshold():
    """TEST 1: Zero penalties -> SWI = 100.0 OPTIMAL."""
    metrics = SWIMetrics(total_trips=10, holding_penalty_sum=0.0, retention_penalty_sum=0.0)
    dto = SWIEngine().calculate(metrics)
    assert dto.current_value == 100.0
    assert dto.status == KPIStatusEnum.OPTIMAL
    assert dto.variance == 25.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_swi_warning_threshold():
    """TEST 2: Penalty resulting in SWI = 70.0 -> WARNING (>= 60.0 & < 75.0)."""
    metrics = SWIMetrics(total_trips=10, holding_penalty_sum=60.0, retention_penalty_sum=30.0)
    dto = SWIEngine().calculate(metrics)
    assert dto.current_value == 70.0
    assert dto.status == KPIStatusEnum.WARNING
    assert dto.variance == -5.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_swi_critical_threshold():
    """TEST 3: Penalty resulting in SWI = 50.0 -> CRITICAL (< 60.0)."""
    metrics = SWIMetrics(total_trips=10, holding_penalty_sum=100.0, retention_penalty_sum=50.0)
    dto = SWIEngine().calculate(metrics)
    assert dto.current_value == 50.0
    assert dto.status == KPIStatusEnum.CRITICAL
    assert dto.variance == -25.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_swi_holding_boundary_20_mins():
    """TEST 4: Holding exactly 20.0 mins -> 0 penalty."""
    obs = [{"t2a_holding_mins": 20.0, "t2c_retention_mins": 10.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 100.0


def test_swi_retention_boundary_10_mins():
    """TEST 5: Retention exactly 10.0 mins -> 0 penalty."""
    obs = [{"t2a_holding_mins": 15.0, "t2c_retention_mins": 10.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 100.0


def test_swi_holding_below_20_mins():
    """TEST 6: Holding 18.0 mins -> 0 penalty."""
    obs = [{"t2a_holding_mins": 18.0, "t2c_retention_mins": 5.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 100.0


def test_swi_retention_below_10_mins():
    """TEST 7: Retention 8.0 mins -> 0 penalty."""
    obs = [{"t2a_holding_mins": 10.0, "t2c_retention_mins": 8.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 100.0


def test_swi_holding_above_20_mins():
    """TEST 8: Holding 25.0 mins -> 5.0 penalty."""
    obs = [{"t2a_holding_mins": 25.0, "t2c_retention_mins": 10.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 83.3


def test_swi_retention_above_10_mins():
    """TEST 9: Retention 15.0 mins -> 5.0 penalty."""
    obs = [{"t2a_holding_mins": 20.0, "t2c_retention_mins": 15.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 83.3


def test_swi_combined_penalties():
    """TEST 10: Holding 25.0 mins (5 pen) + Retention 15.0 mins (5 pen) -> 10 pen total."""
    obs = [{"t2a_holding_mins": 25.0, "t2c_retention_mins": 15.0}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 66.7
    assert dto.status == KPIStatusEnum.WARNING


def test_swi_zero_observations():
    """TEST 11: Zero observations -> None, NO_OBSERVATIONS."""
    metrics = SWIMetrics(total_trips=0, holding_penalty_sum=0.0, retention_penalty_sum=0.0)
    dto = SWIEngine().calculate(metrics)
    assert dto.current_value is None
    assert dto.variance is None
    assert dto.status == KPIStatusEnum.NEUTRAL
    assert dto.availability == AvailabilityEnum.NO_OBSERVATIONS


def test_swi_null_duration_semantics():
    """TEST 12: NULL holding & retention observations contribute 0 penalty."""
    obs = [{"t2a_holding_mins": None, "t2c_retention_mins": None}]
    dto = SWIEngine().calculate(obs)
    assert dto.current_value == 100.0


def test_swi_lower_bound_clamping():
    """TEST 13: Lower-bound clamping at 0.0 when penalties exceed max possible penalty."""
    metrics = SWIMetrics(total_trips=1, holding_penalty_sum=50.0, retention_penalty_sum=50.0)
    dto = SWIEngine().calculate(metrics)
    assert dto.current_value == 0.0
    assert dto.status == KPIStatusEnum.CRITICAL


# === WS-03.1 PHASE 4 DISPATCH PLANNING INDEX (DPI) ENGINE UNIT TESTS ===

def test_dpi_optimal_threshold():
    """TEST 1: 10 eligible intervals, all compliant -> 100.0 OPTIMAL."""
    cust_id = uuid4()
    obs = [
        DPIObservation(
            dispatch_id=uuid4(),
            customer_id=cust_id,
            time_out=f"{i:02d}:00:00",
            t1_transit_mins=20.0,
            t2b_unloading_mins=20.0,
        )
        for i in range(11)
    ]
    dto = DPIEngine().calculate(obs)
    assert dto.current_value == 100.0
    assert dto.status == KPIStatusEnum.OPTIMAL
    assert dto.variance == 15.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_dpi_warning_threshold():
    """TEST 2: 10 eligible intervals, 7 compliant, 3 non-compliant -> 70.0% WARNING."""
    cust_id = uuid4()
    obs = []
    for i in range(8):
        obs.append(
            DPIObservation(
                dispatch_id=uuid4(),
                customer_id=cust_id,
                time_out=time(i, 0, 0),
                t1_transit_mins=20.0,
                t2b_unloading_mins=20.0,
            )
        )
    obs.append(DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out=time(7, 10, 0), t1_transit_mins=20.0, t2b_unloading_mins=20.0))
    obs.append(DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out=time(7, 20, 0), t1_transit_mins=20.0, t2b_unloading_mins=20.0))
    obs.append(DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out=time(7, 30, 0), t1_transit_mins=20.0, t2b_unloading_mins=20.0))

    dto = DPIEngine().calculate(obs)
    assert dto.current_value == 70.0
    assert dto.status == KPIStatusEnum.WARNING
    assert dto.variance == -15.0


def test_dpi_critical_threshold():
    """TEST 3: 10 eligible intervals, 5 compliant, 5 non-compliant -> 50.0% CRITICAL."""
    cust_id = uuid4()
    obs = []
    for i in range(6):
        obs.append(DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out=time(i, 0, 0), t1_transit_mins=20.0, t2b_unloading_mins=20.0))
    for i in range(1, 6):
        obs.append(DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out=time(5, i * 5, 0), t1_transit_mins=20.0, t2b_unloading_mins=20.0))

    dto = DPIEngine().calculate(obs)
    assert dto.current_value == 50.0
    assert dto.status == KPIStatusEnum.CRITICAL
    assert dto.variance == -35.0


def test_dpi_zero_observations():
    """TEST 5: Empty observation list -> BASELINE_UNAVAILABLE, NEUTRAL."""
    dto = DPIEngine().calculate([])
    assert dto.current_value is None
    assert dto.variance is None
    assert dto.status == KPIStatusEnum.NEUTRAL
    assert dto.availability == AvailabilityEnum.BASELINE_UNAVAILABLE


def test_dpi_missing_t1_t2b_excluded():
    """TEST 6: Trips with NULL t1_transit_mins or t2b_unloading_mins are EXCLUDED."""
    cust_id = uuid4()
    obs = [
        DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out="10:00:00", t1_transit_mins=20.0, t2b_unloading_mins=20.0),
        DPIObservation(dispatch_id=uuid4(), customer_id=cust_id, time_out="11:00:00", t1_transit_mins=None, t2b_unloading_mins=20.0),
    ]
    dto = DPIEngine().calculate(obs)
    assert dto.current_value is None
    assert dto.availability == AvailabilityEnum.BASELINE_UNAVAILABLE


# === WS-03.1 PHASE 5 FLEET UTILIZATION INDEX (FUI) ENGINE UNIT TESTS ===

def test_fui_optimal_threshold():
    """TEST 1: 20 active out of 24 registered -> 83.3 / 100 OPTIMAL (>= 70.0)."""
    metrics = FUIMetrics(active_vehicles=20, registered_fleet_denominator=24)
    dto = FUIEngine().calculate(metrics)
    assert dto.current_value == 83.3
    assert dto.status == KPIStatusEnum.OPTIMAL
    assert dto.variance == 13.3
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_fui_warning_threshold():
    """TEST 2: 14 active out of 24 registered -> 58.3 / 100 WARNING (>= 50.0 and < 70.0)."""
    metrics = FUIMetrics(active_vehicles=14, registered_fleet_denominator=24)
    dto = FUIEngine().calculate(metrics)
    assert dto.current_value == 58.3
    assert dto.status == KPIStatusEnum.WARNING
    assert dto.variance == -11.7
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_fui_critical_threshold():
    """TEST 3: 10 active out of 24 registered -> 41.7 / 100 CRITICAL (< 50.0)."""
    metrics = FUIMetrics(active_vehicles=10, registered_fleet_denominator=24)
    dto = FUIEngine().calculate(metrics)
    assert dto.current_value == 41.7
    assert dto.status == KPIStatusEnum.CRITICAL
    assert dto.variance == -28.3
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_fui_full_utilization_cap():
    """TEST 4: 24 active out of 24 registered -> 100.0 / 100 OPTIMAL."""
    metrics = FUIMetrics(active_vehicles=24, registered_fleet_denominator=24)
    dto = FUIEngine().calculate(metrics)
    assert dto.current_value == 100.0
    assert dto.status == KPIStatusEnum.OPTIMAL
    assert dto.variance == 30.0


def test_fui_zero_active_vehicles():
    """TEST 5: 0 active out of 24 registered -> 0.0 / 100 CRITICAL."""
    metrics = FUIMetrics(active_vehicles=0, registered_fleet_denominator=24)
    dto = FUIEngine().calculate(metrics)
    assert dto.current_value == 0.0
    assert dto.status == KPIStatusEnum.CRITICAL
    assert dto.variance == -70.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_fui_zero_denominator():
    """TEST 6: Zero registered fleet denominator -> 0.0 / 100 CRITICAL."""
    metrics = FUIMetrics(active_vehicles=0, registered_fleet_denominator=0)
    dto = FUIEngine().calculate(metrics)
    assert dto.current_value == 0.0
    assert dto.status == KPIStatusEnum.CRITICAL
    assert dto.variance == -70.0
    assert dto.availability == AvailabilityEnum.AVAILABLE


# === WS-03.1 PHASE 6 TOTAL DISPATCHES ENGINE UNIT TESTS ===

def test_total_dispatches_valid_count():
    """TEST 1: 3532 dispatches -> current_value = 3532.0, AVAILABLE, NEUTRAL."""
    dto = TotalDispatchesEngine().calculate(3532)
    assert dto.current_value == 3532.0
    assert dto.unit == "Trips"
    assert dto.target is None
    assert dto.variance is None
    assert dto.total_volume_m3 is None
    assert dto.status == KPIStatusEnum.NEUTRAL
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_total_dispatches_zero_count():
    """TEST 2: 0 dispatches -> current_value = 0.0, AVAILABLE (valid measured zero count)."""
    dto = TotalDispatchesEngine().calculate(0)
    assert dto.current_value == 0.0
    assert dto.unit == "Trips"
    assert dto.status == KPIStatusEnum.NEUTRAL
    assert dto.availability == AvailabilityEnum.AVAILABLE


def test_total_dispatches_none_count():
    """TEST 3: None count -> current_value = None, NO_OBSERVATIONS, NEUTRAL."""
    dto = TotalDispatchesEngine().calculate(None)
    assert dto.current_value is None
    assert dto.status == KPIStatusEnum.NEUTRAL
    assert dto.availability == AvailabilityEnum.NO_OBSERVATIONS


# === LIVE POSTGRESQL FILTER PROPAGATION TESTS ===

@pytest.mark.asyncio
async def test_filter_propagation_suite():
    """TEST E1: Comprehensive Live PostgreSQL Filter Propagation Suite for Accuracy, SWI, DPI, FUI, and Total Dispatches."""
    async with AsyncSessionFactory() as session:
        # E1.1: ALL + ALL + REAL_ONLY
        ribbon_all = await ExecutiveKPIService.get_kpi_ribbon(
            session, DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="REAL_ONLY")
        )
        assert ribbon_all.kpis.dispatch_accuracy.current_value == 63.2
        assert ribbon_all.kpis.swi.current_value == 46.6
        assert ribbon_all.kpis.dpi.current_value == 8.2
        assert ribbon_all.kpis.fui.current_value == 100.0
        assert ribbon_all.kpis.total_dispatches.current_value == 3532.0
        assert ribbon_all.kpis.total_dispatches.total_volume_m3 is None
        assert ribbon_all.kpis.total_dispatches.status == KPIStatusEnum.NEUTRAL
        assert ribbon_all.kpis.total_dispatches.availability == AvailabilityEnum.AVAILABLE

        # E1.2: Specific Plant ACC_VASCO
        ribbon_vasco = await ExecutiveKPIService.get_kpi_ribbon(
            session, DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="REAL_ONLY")
        )
        assert ribbon_vasco.kpis.fui.current_value == 100.0
        assert ribbon_vasco.kpis.total_dispatches.current_value == 1174.0

        # E1.3: Plant + Customer ACC_KUNDAIM + CUST_AARA_HOTELS
        ribbon_kundaim = await ExecutiveKPIService.get_kpi_ribbon(
            session, DashboardFilterParams(plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS", dataset_type="REAL_ONLY")
        )
        assert ribbon_kundaim.kpis.total_dispatches.current_value == 3.0

        # E1.4: SYNTHETIC_ONLY -> 0.0 count
        ribbon_synth = await ExecutiveKPIService.get_kpi_ribbon(
            session, DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="SYNTHETIC_ONLY")
        )
        assert ribbon_synth.kpis.total_dispatches.current_value == 0.0
        assert ribbon_synth.kpis.total_dispatches.status == KPIStatusEnum.NEUTRAL
        assert ribbon_synth.kpis.total_dispatches.availability == AvailabilityEnum.AVAILABLE
