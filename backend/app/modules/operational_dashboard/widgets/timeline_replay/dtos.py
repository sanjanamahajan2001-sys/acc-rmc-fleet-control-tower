"""
WS-08.3 Timeline Replay Data Transfer Objects (DTOs).
Standardized, frozen API contracts for WS-08.3 Timeline Replay.
Supports string or UUID coercible fields for WS-08.2 Timeline Engine compatibility.
"""
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class EventAuthorityEnum(str, Enum):
    DIRECT = "DIRECT"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNAVAILABLE = "UNAVAILABLE"


class SpatialModeEnum(str, Enum):
    GPS_TRAJECTORY = "GPS_TRAJECTORY"
    LOCATION_CONTEXT_ONLY = "LOCATION_CONTEXT_ONLY"
    NO_SPATIAL_DATA = "NO_SPATIAL_DATA"


class DurationCompletenessEnum(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


# Class Aliases for WS-08.1/WS-08.2 DTO class naming compatibility
EventAuthorityDTO = EventAuthorityEnum
SpatialModeDTO = SpatialModeEnum


class TimelineEventItemDTO(BaseModel):
    event_type: str = Field(..., description="Scheduled | Batched | Loaded | Departed Plant | Arrived Site | Unloading / Pouring | Completed | Returned")
    authority_type: EventAuthorityEnum = Field(..., description="DIRECT | DERIVED | INFERRED | UNAVAILABLE")
    timestamp: Optional[datetime] = Field(None, description="ISO-8601 UTC Event Timestamp")
    duration_mins: Optional[float] = Field(None, description="Duration in minutes from previous event")
    location_name: Optional[str] = Field(None, description="Plant or Site name if available")
    is_inferred_estimate: bool = Field(False, description="Flag indicating inferred estimate (e.g. Loaded = Departure - 10m)")
    notes: Optional[str] = Field(None, description="Audit notes or derivation rationale")


class DurationSummaryDTO(BaseModel):
    total_trip_duration_mins: Optional[float] = Field(None, description="Physical trip duration (Departed Plant to Returned/Completed)")
    duration_completeness: DurationCompletenessEnum = Field(..., description="COMPLETE | PARTIAL | UNAVAILABLE")
    missing_segments: List[str] = Field(default_factory=list, description="List of missing segment identifiers, e.g. ['T3_RETURN']")


# Class Alias for DurationSummaryDTO / DurationCompletenessEnum compatibility
DurationCompletenessDTO = DurationSummaryDTO


class TelemetrySummaryDTO(BaseModel):
    avg_speed_kmh: Optional[float] = Field(None, description="Average trip speed in km/h if available")
    max_speed_kmh: Optional[float] = Field(None, description="Peak trip speed in km/h if available")
    drum_rotation_rpm: Optional[float] = Field(None, description="Average drum rotation RPM during unloading if available")
    telemetry_matched: bool = Field(..., description="Flag indicating correlated telemetry record exists")


class TrajectoryPointDTO(BaseModel):
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    timestamp: Optional[datetime] = Field(None, description="ISO-8601 UTC Timestamp")
    speed_kmh: Optional[float] = Field(None, description="Instantaneous speed in km/h if available")
    heading_deg: Optional[float] = Field(None, description="Heading/bearing in degrees if available")


class SpatialContextDTO(BaseModel):
    has_gps_breadcrumbs: bool = Field(..., description="Flag indicating presence of GPS breadcrumbs")
    spatial_mode: SpatialModeEnum = Field(..., description="GPS_TRAJECTORY | LOCATION_CONTEXT_ONLY | NO_SPATIAL_DATA")
    plant_latitude: Optional[float] = Field(None, description="Plant latitude for location context")
    plant_longitude: Optional[float] = Field(None, description="Plant longitude for location context")
    site_latitude: Optional[float] = Field(None, description="Site latitude for location context")
    site_longitude: Optional[float] = Field(None, description="Site longitude for location context")
    trajectory_points: List[TrajectoryPointDTO] = Field(default_factory=list, description="Array of GPS trajectory points (Empty if no breadcrumbs)")


class DispatchReplayListItemDTO(BaseModel):
    dispatch_id: str = Field(..., description="Dispatch UUID string")
    dispatch_number: str = Field(..., description="ERP Dispatch / Ticket number")
    plant_id: str = Field(..., description="Plant UUID string")
    customer_id: str = Field(..., description="Customer UUID string")
    raw_customer_name: Optional[str] = Field(None, description="Raw ERP Customer Name")
    customer_name: Optional[str] = Field(None, description="Effective Customer Display Name")
    effective_customer_name: Optional[str] = Field(None, description="Effective Customer Display Name")
    vehicle_id: Optional[str] = Field(None, description="Vehicle UUID string")
    dispatch_date: datetime = Field(..., description="ISO-8601 Dispatch Date")
    status: str = Field(..., description="Dispatch status")
    has_telemetry: bool = Field(..., description="Indicates if telemetry is matched")


class DispatchReplayListResponseDTO(BaseModel):
    items: List[DispatchReplayListItemDTO]
    total_count: int = Field(..., description="Total matching dispatches count across scope")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")


class DispatchTimelineReplayDetailDTO(BaseModel):
    dispatch_id: Union[str, UUID] = Field(..., description="Dispatch UUID or string")
    dispatch_number: str = Field(..., description="ERP Dispatch / Ticket number")
    plant_id: Union[str, UUID] = Field(..., description="Plant UUID or string")
    customer_id: Union[str, UUID] = Field(..., description="Customer UUID or string")
    raw_customer_name: Optional[str] = Field(None, description="Raw ERP Customer Name")
    customer_name: Optional[str] = Field(None, description="Effective Customer Display Name")
    effective_customer_name: Optional[str] = Field(None, description="Effective Customer Display Name")
    vehicle_id: Optional[Union[str, UUID]] = Field(None, description="Vehicle UUID or string")
    dataset_id: Optional[Union[str, UUID]] = Field(None, description="Import batch / dataset UUID or string")
    status: str = Field(..., description="Dispatch status")
    duration_summary: DurationSummaryDTO = Field(..., description="Trip duration breakdown and completeness metrics")
    t2c_retention_mins: Optional[float] = Field(None, description="T2c Excess Retention SLA metric (Retained separately from physical trip duration)")
    lifecycle_events: List[TimelineEventItemDTO] = Field(..., description="8-phase timeline events array with authority classification")
    telemetry_summary: TelemetrySummaryDTO = Field(..., description="Telemetry metric aggregates if available")
    spatial_context: SpatialContextDTO = Field(..., description="Spatial capability context (GPS breadcrumbs or location context)")
    correlated_alert_count: int = Field(0, description="Read-only count of correlated WS-07 operational alerts")
