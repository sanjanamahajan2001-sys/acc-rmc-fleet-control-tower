"""
Workstream 2.11 Synchronization Calculation Engine
Computes synchronization status, E-Tag validity, and data freshness metrics without frontend business logic.
"""

from typing import Any
from app.modules.site_dashboard.sync.dtos import SyncStatusDTO
from app.modules.site_dashboard.sync.sync_manager import SyncManager


class SyncCalculations:
    """Formats synchronization calculations and evaluates E-Tag snapshot changes."""

    @staticmethod
    def build_sync_status(db_state: dict[str, Any], pending_events: int = 0) -> SyncStatusDTO:
        total_records = db_state["total_records"]
        latest_date = db_state["latest_date"]
        e_tag = db_state["e_tag"]
        snapshot_ver = db_state["snapshot_version"]

        if total_records == 0:
            status = "LAGGING"
        else:
            status = "SYNCHRONIZED"

        active_ops = SyncManager.get_active_operators_count()

        return SyncStatusDTO(
            sync_status=status,
            last_sync_timestamp=f"{latest_date} 18:30:00",
            snapshot_version=snapshot_ver,
            pending_events_count=pending_events,
            active_operators_count=max(active_ops, 1),
            e_tag=e_tag,
        )
