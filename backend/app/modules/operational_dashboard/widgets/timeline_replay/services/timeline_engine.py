"""
WS-08.2 Digital Twin Lifecycle & Timeline Calculation Engine.
Pure backend domain logic translating authoritative dispatch and telemetry model inputs into DTO outputs.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID

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


class TimelineReplayEngine:
    """
    Deterministic Digital Twin Lifecycle & Timeline Calculation Engine for WS-08.2.
    Translates raw PostgreSQL dispatch & telemetry records into authoritative lifecycle timeline DTOs.
    """

    @staticmethod
    def _parse_hhmmss(date_base: datetime, time_str: Optional[str]) -> Optional[datetime]:
        """Helper parsing HH:MM:SS string onto a base datetime in UTC."""
        if not time_str or not isinstance(time_str, str):
            return None
        parts = time_str.strip().split(":")
        if len(parts) < 2:
            return None
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59:
                return None
            return date_base.replace(hour=hours, minute=minutes, second=seconds, microsecond=0, tzinfo=timezone.utc)
        except ValueError:
            return None

    @classmethod
    def calculate_dispatch_timeline(
        cls,
        dispatch: Dict[str, Any],
        telemetry: Optional[Dict[str, Any]] = None,
        plant: Optional[Dict[str, Any]] = None,
        site: Optional[Dict[str, Any]] = None,
        correlated_alert_count: int = 0,
    ) -> DispatchTimelineReplayDetailDTO:
        """
        Calculates authoritative chronological lifecycle events, duration completeness,
        spatial capability context, and telemetry metrics for a single dispatch.
        """
        dispatch_id = dispatch.get("id")
        dispatch_number = dispatch.get("dispatch_number", "UNKNOWN")
        plant_id = dispatch.get("plant_id")
        customer_id = dispatch.get("customer_id")
        vehicle_id = dispatch.get("vehicle_id")
        dataset_id = dispatch.get("import_batch_id")
        status = dispatch.get("status", "UNKNOWN")

        dispatch_date = dispatch.get("dispatch_date")
        if not isinstance(dispatch_date, datetime):
            dispatch_date = datetime.now(timezone.utc)

        # 1. Resolve Individual Event Timestamps
        # Scheduled: System-record scheduling proxy
        ts_scheduled = dispatch_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Batched: Direct ERP batching timestamp
        ts_batched = dispatch_date
        
        # Departed Plant: Direct/Derived from dispatch.time_out string
        ts_departed = cls._parse_hhmmss(dispatch_date, dispatch.get("time_out"))
        
        # Telemetry priority for timestamps
        tel_out = telemetry.get("plant_out_timestamp") if telemetry else None
        tel_arrival = telemetry.get("site_arrival_timestamp") if telemetry else None
        tel_unload_start = telemetry.get("unloading_start_timestamp") if telemetry else None
        tel_unload_end = telemetry.get("unloading_end_timestamp") if telemetry else None
        tel_return = telemetry.get("plant_return_timestamp") if telemetry else None

        if tel_out and isinstance(tel_out, datetime):
            ts_departed = tel_out

        # Loaded: INFERRED 10 minutes prior to departure
        ts_loaded = ts_departed - timedelta(minutes=10) if ts_departed else None

        # Arrived Site
        t1_transit_mins = dispatch.get("t1_transit_mins")
        ts_arrived = tel_arrival
        if not ts_arrived and ts_departed and t1_transit_mins is not None and t1_transit_mins >= 0:
            ts_arrived = ts_departed + timedelta(minutes=t1_transit_mins)

        # Unloading / Pouring
        t2a_holding_mins = dispatch.get("t2a_holding_mins")
        ts_unloading_start = tel_unload_start
        if not ts_unloading_start and ts_arrived and t2a_holding_mins is not None and t2a_holding_mins >= 0:
            ts_unloading_start = ts_arrived + timedelta(minutes=t2a_holding_mins)

        # Completed (Unloading End)
        t2b_unloading_mins = dispatch.get("t2b_unloading_mins")
        ts_completed = tel_unload_end
        if not ts_completed and ts_unloading_start and t2b_unloading_mins is not None and t2b_unloading_mins >= 0:
            ts_completed = ts_unloading_start + timedelta(minutes=t2b_unloading_mins)

        # Returned
        ts_returned = tel_return
        if not ts_returned:
            ts_returned = cls._parse_hhmmss(dispatch_date, dispatch.get("time_in"))

        # Chronology Validation & Invalid Data Handling
        # If departure is before batching, mark departure invalid
        if ts_departed and ts_batched and ts_departed < ts_batched:
            ts_departed = None
            ts_loaded = None
        if ts_arrived and ts_departed and ts_arrived < ts_departed:
            ts_arrived = None
        if ts_unloading_start and ts_arrived and ts_unloading_start < ts_arrived:
            ts_unloading_start = None
        if ts_completed and ts_unloading_start and ts_completed < ts_unloading_start:
            ts_completed = None
        if ts_returned and ts_completed and ts_returned < ts_completed:
            ts_returned = None

        # 2. Build Lifecycle Event Items
        events: List[TimelineEventItemDTO] = []

        # Scheduled
        events.append(TimelineEventItemDTO(
            event_type="Scheduled",
            authority_type=EventAuthorityEnum.DERIVED,
            timestamp=ts_scheduled,
            duration_mins=0.0,
            location_name=plant.get("name") if plant else None,
            is_inferred_estimate=False,
            notes="System-record scheduling proxy derived from dispatch date (00:00 UTC)."
        ))

        # Batched
        events.append(TimelineEventItemDTO(
            event_type="Batched",
            authority_type=EventAuthorityEnum.DIRECT,
            timestamp=ts_batched,
            duration_mins=(ts_batched - ts_scheduled).total_seconds() / 60.0 if ts_scheduled else None,
            location_name=plant.get("name") if plant else None,
            is_inferred_estimate=False,
            notes="Authoritative concrete batching timestamp from ERP ticket."
        ))

        # Loaded
        events.append(TimelineEventItemDTO(
            event_type="Loaded",
            authority_type=EventAuthorityEnum.INFERRED,
            timestamp=ts_loaded,
            duration_mins=(ts_loaded - ts_batched).total_seconds() / 60.0 if (ts_loaded and ts_batched and ts_loaded >= ts_batched) else None,
            location_name=plant.get("name") if plant else None,
            is_inferred_estimate=True,
            notes="Inferred estimate: Estimated 10 minutes prior to departure timestamp. No physical loading timestamp exists in production schema."
        ))

        # Departed Plant
        events.append(TimelineEventItemDTO(
            event_type="Departed Plant",
            authority_type=EventAuthorityEnum.DIRECT if tel_out else EventAuthorityEnum.DERIVED,
            timestamp=ts_departed,
            duration_mins=(ts_departed - ts_loaded).total_seconds() / 60.0 if (ts_departed and ts_loaded) else None,
            location_name=plant.get("name") if plant else None,
            is_inferred_estimate=False,
            notes="Authoritative departure timestamp from telemetry or ERP time_out."
        ))

        # Arrived Site
        events.append(TimelineEventItemDTO(
            event_type="Arrived Site",
            authority_type=EventAuthorityEnum.DIRECT if tel_arrival else (EventAuthorityEnum.DERIVED if ts_arrived else EventAuthorityEnum.UNAVAILABLE),
            timestamp=ts_arrived,
            duration_mins=t1_transit_mins if (t1_transit_mins is not None and t1_transit_mins >= 0) else None,
            location_name=site.get("name") if site else None,
            is_inferred_estimate=False,
            notes="Job site geofence entry timestamp."
        ))

        # Unloading / Pouring
        events.append(TimelineEventItemDTO(
            event_type="Unloading / Pouring",
            authority_type=EventAuthorityEnum.DIRECT if tel_unload_start else (EventAuthorityEnum.DERIVED if ts_unloading_start else EventAuthorityEnum.UNAVAILABLE),
            timestamp=ts_unloading_start,
            duration_mins=t2a_holding_mins if (t2a_holding_mins is not None and t2a_holding_mins >= 0) else None,
            location_name=site.get("name") if site else None,
            is_inferred_estimate=False,
            notes="Site slump inspection completed; concrete discharge initiated."
        ))

        # Completed
        events.append(TimelineEventItemDTO(
            event_type="Completed",
            authority_type=EventAuthorityEnum.DIRECT if tel_unload_end else (EventAuthorityEnum.DERIVED if ts_completed else EventAuthorityEnum.UNAVAILABLE),
            timestamp=ts_completed,
            duration_mins=t2b_unloading_mins if (t2b_unloading_mins is not None and t2b_unloading_mins >= 0) else None,
            location_name=site.get("name") if site else None,
            is_inferred_estimate=False,
            notes="Concrete discharge completed."
        ))

        # Returned
        t3_return_mins = dispatch.get("t3_return_mins")
        events.append(TimelineEventItemDTO(
            event_type="Returned",
            authority_type=EventAuthorityEnum.DIRECT if tel_return else (EventAuthorityEnum.DERIVED if ts_returned else EventAuthorityEnum.UNAVAILABLE),
            timestamp=ts_returned,
            duration_mins=t3_return_mins if (ts_returned and ts_completed and t3_return_mins is not None and t3_return_mins >= 0) else None,
            location_name=plant.get("name") if plant else None,
            is_inferred_estimate=False,
            notes="Mixer truck return to plant geofence."
        ))

        # 3. Calculate Durations & Completeness
        missing_segments: List[str] = []
        if t1_transit_mins is None or t1_transit_mins < 0:
            missing_segments.append("T1_TRANSIT")
        if t2a_holding_mins is None or t2a_holding_mins < 0:
            missing_segments.append("T2A_HOLDING")
        if t2b_unloading_mins is None or t2b_unloading_mins < 0:
            missing_segments.append("T2B_UNLOADING")
        
        # T3 Return missing-data rule: Site Departure -> Plant Return
        if not ts_returned or not ts_completed or t3_return_mins is None or t3_return_mins < 0:
            missing_segments.append("T3_RETURN")

        valid_durations = [d for d in [t1_transit_mins, t2a_holding_mins, t2b_unloading_mins, (t3_return_mins if "T3_RETURN" not in missing_segments else None)] if d is not None and d >= 0]
        total_trip_duration = sum(valid_durations) if valid_durations else None

        if len(missing_segments) == 0 and total_trip_duration is not None:
            completeness = DurationCompletenessEnum.COMPLETE
        elif total_trip_duration is not None:
            completeness = DurationCompletenessEnum.PARTIAL
        else:
            completeness = DurationCompletenessEnum.UNAVAILABLE

        duration_summary = DurationCompletenessDTO(
            total_trip_duration_mins=total_trip_duration,
            duration_completeness=completeness,
            missing_segments=missing_segments
        )

        # 4. Telemetry Summary
        telemetry_matched = bool(telemetry and telemetry.get("correlation_status") == "MATCHED")
        telemetry_summary = TelemetrySummaryDTO(
            avg_speed_kmh=telemetry.get("avg_speed_kmh") if telemetry else None,
            max_speed_kmh=telemetry.get("max_speed_kmh") if telemetry else None,
            drum_rotation_rpm=telemetry.get("drum_rotation_rpm") if telemetry else None,
            telemetry_matched=telemetry_matched
        )

        # 5. Spatial Capability Context
        plant_lat = plant.get("latitude") if plant else None
        plant_lon = plant.get("longitude") if plant else None
        site_lat = site.get("latitude") if site else None
        site_lon = site.get("longitude") if site else None

        # Check GPS breadcrumbs (0 synthetic GPS generated)
        has_gps = False
        trajectory_points: List[TrajectoryPointDTO] = []

        if has_gps:
            spatial_mode = SpatialModeEnum.GPS_TRAJECTORY
        elif plant_lat is not None and plant_lon is not None and site_lat is not None and site_lon is not None:
            spatial_mode = SpatialModeEnum.LOCATION_CONTEXT_ONLY
        else:
            spatial_mode = SpatialModeEnum.NO_SPATIAL_DATA

        spatial_context = SpatialContextDTO(
            has_gps_breadcrumbs=has_gps,
            spatial_mode=spatial_mode,
            plant_latitude=plant_lat,
            plant_longitude=plant_lon,
            site_latitude=site_lat,
            site_longitude=site_lon,
            trajectory_points=trajectory_points
        )

        # 6. T2c Excess Site Retention SLA Metric (WS-05/WS-03 Boundary)
        t2c_retention_mins = dispatch.get("t2c_retention_mins")
        raw_customer_name = dispatch.get("raw_customer_name")
        effective_customer_name = dispatch.get("effective_customer_name") or dispatch.get("customer_name") or raw_customer_name

        return DispatchTimelineReplayDetailDTO(
            dispatch_id=dispatch_id,
            dispatch_number=dispatch_number,
            plant_id=plant_id,
            customer_id=customer_id,
            raw_customer_name=raw_customer_name,
            customer_name=effective_customer_name,
            effective_customer_name=effective_customer_name,
            vehicle_id=vehicle_id,
            dataset_id=dataset_id,
            status=status,
            duration_summary=duration_summary,
            t2c_retention_mins=t2c_retention_mins,
            lifecycle_events=events,
            telemetry_summary=telemetry_summary,
            spatial_context=spatial_context,
            correlated_alert_count=correlated_alert_count
        )
