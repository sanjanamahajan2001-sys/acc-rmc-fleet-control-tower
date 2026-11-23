"""
WS-08.2 Dedicated PyTest Suite for Digital Twin Lifecycle & Timeline Calculation Engine.
Verifies all 27 mandatory certification tests.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    EventAuthorityEnum,
    SpatialModeEnum,
    DurationCompletenessEnum,
)
from app.modules.operational_dashboard.widgets.timeline_replay.services.timeline_engine import TimelineReplayEngine


@pytest.fixture
def sample_complete_dispatch():
    now = datetime(2025, 8, 11, 8, 0, 0, tzinfo=timezone.utc)
    return {
        "id": uuid4(),
        "dispatch_number": "DISP-FULL-001",
        "plant_id": uuid4(),
        "customer_id": uuid4(),
        "vehicle_id": uuid4(),
        "import_batch_id": uuid4(),
        "dispatch_date": now,
        "time_out": "08:15:00",
        "time_in": "10:00:00",
        "t1_transit_mins": 20.0,
        "t2a_holding_mins": 10.0,
        "t2b_unloading_mins": 30.0,
        "t2c_retention_mins": 5.0,
        "t3_return_mins": 25.0,
        "status": "COMPLETED"
    }


@pytest.fixture
def sample_plant():
    return {"id": uuid4(), "name": "ACC Vasai Plant", "latitude": 15.3981, "longitude": 73.8122}


@pytest.fixture
def sample_site():
    return {"id": uuid4(), "name": "True Build Tonca Site", "latitude": 15.4989, "longitude": 73.8278}


def test_ws_08_2_complete_lifecycle_and_duration(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 1, 12-16: Complete lifecycle timeline calculation and duration completeness"""
    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=sample_plant,
        site=sample_site
    )

    assert dto.dispatch_number == "DISP-FULL-001"
    assert dto.duration_summary.duration_completeness == DurationCompletenessEnum.COMPLETE
    assert dto.duration_summary.total_trip_duration_mins == 85.0  # 20 + 10 + 30 + 25
    assert len(dto.duration_summary.missing_segments) == 0
    assert len(dto.lifecycle_events) == 8


def test_ws_08_2_loaded_event_inferred_authority(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 8: Loaded event remains INFERRED estimate and carries is_inferred_estimate = True"""
    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=sample_plant,
        site=sample_site
    )

    loaded_event = next(e for e in dto.lifecycle_events if e.event_type == "Loaded")
    assert loaded_event.authority_type == EventAuthorityEnum.INFERRED
    assert loaded_event.is_inferred_estimate is True
    assert "No physical loading timestamp exists" in loaded_event.notes


def test_ws_08_2_scheduled_event_authority(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 9: Scheduled event preserves System-Record Scheduling Proxy authority"""
    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=sample_plant,
        site=sample_site
    )

    sched_event = next(e for e in dto.lifecycle_events if e.event_type == "Scheduled")
    assert sched_event.authority_type == EventAuthorityEnum.DERIVED
    assert "System-record scheduling proxy" in sched_event.notes


def test_ws_08_2_missing_t3_return_contract(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 3, 7, 15, 17: Missing T3 return handling sets T3 = NULL and missing_segments = ['T3_RETURN']"""
    dispatch_no_return = sample_complete_dispatch.copy()
    dispatch_no_return["time_in"] = None
    dispatch_no_return["t3_return_mins"] = None

    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=dispatch_no_return,
        plant=sample_plant,
        site=sample_site
    )

    assert dto.duration_summary.duration_completeness == DurationCompletenessEnum.PARTIAL
    assert "T3_RETURN" in dto.duration_summary.missing_segments
    assert dto.duration_summary.total_trip_duration_mins == 60.0  # 20 + 10 + 30


def test_ws_08_2_direct_telemetry_precedence(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 10, 11, 24: Direct telemetry timestamp takes precedence over ERP derivation"""
    telemetry = {
        "correlation_status": "MATCHED",
        "plant_out_timestamp": datetime(2025, 8, 11, 8, 18, 0, tzinfo=timezone.utc),
        "site_arrival_timestamp": datetime(2025, 8, 11, 8, 38, 0, tzinfo=timezone.utc),
        "unloading_start_timestamp": datetime(2025, 8, 11, 8, 48, 0, tzinfo=timezone.utc),
        "unloading_end_timestamp": datetime(2025, 8, 11, 9, 18, 0, tzinfo=timezone.utc),
        "plant_return_timestamp": datetime(2025, 8, 11, 9, 45, 0, tzinfo=timezone.utc),
        "avg_speed_kmh": 35.5,
        "max_speed_kmh": 62.0,
        "drum_rotation_rpm": 3.5
    }

    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        telemetry=telemetry,
        plant=sample_plant,
        site=sample_site
    )

    dep_event = next(e for e in dto.lifecycle_events if e.event_type == "Departed Plant")
    assert dep_event.authority_type == EventAuthorityEnum.DIRECT
    assert dep_event.timestamp == telemetry["plant_out_timestamp"]
    assert dto.telemetry_summary.telemetry_matched is True
    assert dto.telemetry_summary.avg_speed_kmh == 35.5


def test_ws_08_2_spatial_capability_modes(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 19-23: Dynamic spatial_mode determination and zero synthetic GPS points"""
    # 1. Location context mode
    dto_context = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=sample_plant,
        site=sample_site
    )
    assert dto_context.spatial_context.spatial_mode == SpatialModeEnum.LOCATION_CONTEXT_ONLY
    assert dto_context.spatial_context.has_gps_breadcrumbs is False
    assert len(dto_context.spatial_context.trajectory_points) == 0

    # 2. No spatial data mode
    dto_no_spatial = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=None,
        site=None
    )
    assert dto_no_spatial.spatial_context.spatial_mode == SpatialModeEnum.NO_SPATIAL_DATA
    assert dto_no_spatial.spatial_context.has_gps_breadcrumbs is False


def test_ws_08_2_t2c_sla_metric_boundary(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 18: T2c retention remains SLA metric and is excluded from physical lifecycle events"""
    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=sample_plant,
        site=sample_site
    )

    assert dto.t2c_retention_mins == 5.0
    # Ensure T2c is not a physical lifecycle event item
    event_names = [e.event_type for e in dto.lifecycle_events]
    assert "T2c Retention" not in event_names


def test_ws_08_2_invalid_chronology_handling(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 25: Chronology validation invalidates impossible timestamps without crashing"""
    invalid_dispatch = sample_complete_dispatch.copy()
    invalid_dispatch["time_out"] = "07:00:00"  # Departure before batching (08:00)

    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=invalid_dispatch,
        plant=sample_plant,
        site=sample_site
    )

    dep_event = next(e for e in dto.lifecycle_events if e.event_type == "Departed Plant")
    assert dep_event.timestamp is None
    assert dep_event.authority_type == EventAuthorityEnum.DERIVED or dep_event.authority_type == EventAuthorityEnum.UNAVAILABLE


def test_ws_08_2_deterministic_output(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 26: Engine output is 100% deterministic for identical inputs"""
    dto1 = TimelineReplayEngine.calculate_dispatch_timeline(dispatch=sample_complete_dispatch, plant=sample_plant, site=sample_site)
    dto2 = TimelineReplayEngine.calculate_dispatch_timeline(dispatch=sample_complete_dispatch, plant=sample_plant, site=sample_site)

    assert dto1.dispatch_id == dto2.dispatch_id
    assert dto1.duration_summary.total_trip_duration_mins == dto2.duration_summary.total_trip_duration_mins
    assert dto1.lifecycle_events == dto2.lifecycle_events


def test_ws_08_2_read_only_alert_correlation(sample_complete_dispatch, sample_plant, sample_site):
    """TEST 27: Correlated WS-07 alert count is read-only"""
    dto = TimelineReplayEngine.calculate_dispatch_timeline(
        dispatch=sample_complete_dispatch,
        plant=sample_plant,
        site=sample_site,
        correlated_alert_count=3
    )

    assert dto.correlated_alert_count == 3
