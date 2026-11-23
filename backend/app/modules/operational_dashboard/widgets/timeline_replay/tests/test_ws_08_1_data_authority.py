"""
WS-08.1 Dedicated Data Authority, Lifecycle & Contract Verification Test Suite (Remediated).
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    EventAuthorityEnum,
    SpatialModeEnum,
    DurationCompletenessEnum,
    TimelineEventItemDTO,
    TelemetrySummaryDTO,
    SpatialContextDTO,
    TrajectoryPointDTO,
    DurationCompletenessDTO,
    DispatchTimelineReplayDetailDTO,
)


def test_ws_08_1_dto_event_authority_classification():
    """TEST 1: Verifies EventAuthorityEnum values (DIRECT, DERIVED, INFERRED, UNAVAILABLE)"""
    event_direct = TimelineEventItemDTO(
        event_type="Batched",
        authority_type=EventAuthorityEnum.DIRECT,
        timestamp=datetime.now(timezone.utc),
        is_inferred_estimate=False
    )
    assert event_direct.authority_type == "DIRECT"
    assert event_direct.is_inferred_estimate is False

    event_inferred = TimelineEventItemDTO(
        event_type="Loaded",
        authority_type=EventAuthorityEnum.INFERRED,
        timestamp=datetime.now(timezone.utc),
        is_inferred_estimate=True,
        notes="Inferred estimate: No physical loading timestamp exists in production schema."
    )
    assert event_inferred.authority_type == "INFERRED"
    assert event_inferred.is_inferred_estimate is True


def test_ws_08_1_dto_spatial_mode_and_typed_trajectory_points():
    """TEST 2: Verifies dynamic spatial_mode without hardcoded default and strongly typed TrajectoryPointDTO"""
    spatial_no_data = SpatialContextDTO(
        has_gps_breadcrumbs=False,
        spatial_mode=SpatialModeEnum.NO_SPATIAL_DATA,
        plant_latitude=None,
        plant_longitude=None,
        site_latitude=None,
        site_longitude=None,
        trajectory_points=[]
    )
    assert spatial_no_data.has_gps_breadcrumbs is False
    assert spatial_no_data.spatial_mode == "NO_SPATIAL_DATA"
    assert len(spatial_no_data.trajectory_points) == 0

    spatial_gps = SpatialContextDTO(
        has_gps_breadcrumbs=True,
        spatial_mode=SpatialModeEnum.GPS_TRAJECTORY,
        plant_latitude=15.3981,
        plant_longitude=73.8122,
        site_latitude=15.4989,
        site_longitude=73.8278,
        trajectory_points=[
            TrajectoryPointDTO(
                latitude=15.4001,
                longitude=73.8150,
                timestamp=datetime.now(timezone.utc),
                speed_kmh=42.5,
                heading_deg=90.0
            )
        ]
    )
    assert spatial_gps.has_gps_breadcrumbs is True
    assert spatial_gps.spatial_mode == "GPS_TRAJECTORY"
    assert len(spatial_gps.trajectory_points) == 1
    assert spatial_gps.trajectory_points[0].speed_kmh == 42.5


def test_ws_08_1_dto_dataset_id_nullability():
    """TEST 5: Verifies dataset_id nullability for legacy or non-imported dispatches"""
    detail = DispatchTimelineReplayDetailDTO(
        dispatch_id=uuid4(),
        dispatch_number="SYNTH-TCK-TRIP-1",
        plant_id=uuid4(),
        customer_id=uuid4(),
        vehicle_id=uuid4(),
        dataset_id=None,  # Nullable for legacy dispatches
        status="COMPLETED",
        duration_summary=DurationCompletenessDTO(
            total_trip_duration_mins=94.0,
            duration_completeness=DurationCompletenessEnum.COMPLETE,
            missing_segments=[]
        ),
        t2c_retention_mins=10.0,
        lifecycle_events=[
            TimelineEventItemDTO(
                event_type="Batched",
                authority_type=EventAuthorityEnum.DIRECT,
                timestamp=datetime.now(timezone.utc)
            )
        ],
        telemetry_summary=TelemetrySummaryDTO(telemetry_matched=False),
        spatial_context=SpatialContextDTO(
            has_gps_breadcrumbs=False,
            spatial_mode=SpatialModeEnum.NO_SPATIAL_DATA
        ),
        correlated_alert_count=0
    )
    assert detail.dataset_id is None
    assert detail.dispatch_number == "SYNTH-TCK-TRIP-1"
