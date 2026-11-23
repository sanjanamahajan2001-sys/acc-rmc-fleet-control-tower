"""
Workstream 2.11 Synchronization DTO Layer
Defines strict schemas for real-time synchronization events, dashboard sync status, and refresh results.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class SyncStatusDTO(BaseModel):
    """Real-time synchronization and data freshness status payload."""
    sync_status: Literal["SYNCHRONIZED", "REFRESHING", "LAGGING", "DISCONNECTED"] = Field(
        ..., description="Current connection & data freshness status badge"
    )
    last_sync_timestamp: str = Field(..., description="Timestamp of last successful synchronization (YYYY-MM-DD HH:MM:SS)")
    snapshot_version: str = Field(..., description="Canonical snapshot version string (e.g. v2.11-SNAP-20250815)")
    pending_events_count: int = Field(..., description="Number of unacknowledged operational sync events")
    active_operators_count: int = Field(..., description="Number of active connected control tower operators")
    e_tag: str = Field(..., description="MD5 hash checksum of current canonical snapshot")


class SyncEventDTO(BaseModel):
    """Real-time event notification payload published over SSE stream."""
    event_id: str = Field(..., description="Unique event identifier (e.g. EVT-SYNC-001)")
    event_type: Literal[
        "ERP_IMPORT_COMPLETED",
        "ERP_RESET_COMPLETED",
        "SNAPSHOT_INVALIDATED",
        "SNAPSHOT_REGENERATED",
        "SLA_BREACH_DETECTED"
    ] = Field(..., description="Classification of operational event")
    timestamp: str = Field(..., description="Event timestamp (YYYY-MM-DD HH:MM:SS)")
    snapshot_version: str = Field(..., description="Snapshot version associated with event")
    details: dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for event details")


class RefreshResultDTO(BaseModel):
    """Payload returned following a manual or automated dashboard refresh execution."""
    success: bool = Field(..., description="True if refresh execution completed cleanly")
    refreshed_at: str = Field(..., description="Execution completion timestamp")
    duration_ms: float = Field(..., description="Total backend refresh duration in milliseconds")
    records_updated: int = Field(..., description="Total records evaluated during refresh")
    new_snapshot_version: str = Field(..., description="Updated canonical snapshot version")
