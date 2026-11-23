"""
Workstream 2.11 Synchronization Service Layer
Orchestrates sync state queries, manual refreshes, and ERP lifecycle events.
"""

import time
from datetime import datetime
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.sync.repository import SyncRepository
from app.modules.site_dashboard.sync.calculations import SyncCalculations
from app.modules.site_dashboard.sync.sync_manager import SyncManager
from app.modules.site_dashboard.sync.dtos import SyncStatusDTO, RefreshResultDTO, SyncEventDTO


class SyncService:
    """Orchestrates real-time synchronization services and ERP lifecycle notifications."""

    @staticmethod
    async def get_sync_status(session: AsyncSession) -> SyncStatusDTO:
        """Returns the current real-time dashboard sync status."""
        db_state = await SyncRepository.get_latest_db_state(session)
        return SyncCalculations.build_sync_status(db_state)

    @staticmethod
    async def trigger_manual_refresh(session: AsyncSession) -> RefreshResultDTO:
        """Triggers a manual or automated dashboard snapshot refresh."""
        t0 = time.perf_counter()
        db_state = await SyncRepository.get_latest_db_state(session)
        t1 = time.perf_counter()
        dur_ms = (t1 - t0) * 1000.0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Broadcast refresh completion event over SSE stream
        await SyncManager.publish_event(
            event_type="SNAPSHOT_REGENERATED",
            snapshot_version=db_state["snapshot_version"],
            details={"refreshed_at": now_str, "records": db_state["total_records"]}
        )

        return RefreshResultDTO(
            success=True,
            refreshed_at=now_str,
            duration_ms=round(dur_ms, 1),
            records_updated=db_state["total_records"],
            new_snapshot_version=db_state["snapshot_version"],
        )

    @staticmethod
    async def notify_erp_reset(session: AsyncSession) -> SyncEventDTO:
        """Publishes instant ERP_RESET_COMPLETED and SNAPSHOT_INVALIDATED events over SSE."""
        db_state = await SyncRepository.get_latest_db_state(session)
        
        # Publish invalidation followed by reset completion
        await SyncManager.publish_event(
            event_type="SNAPSHOT_INVALIDATED",
            snapshot_version=db_state["snapshot_version"],
            details={"action": "DATABASE_CLEAR_INITIATED"}
        )

        evt = await SyncManager.publish_event(
            event_type="ERP_RESET_COMPLETED",
            snapshot_version="v2.11-SNAP-EMPTY",
            details={"action": "DATABASE_CLEAR_COMPLETED"}
        )
        return evt

    @staticmethod
    async def notify_erp_import(session: AsyncSession, imported_records: int = 0) -> SyncEventDTO:
        """Publishes ERP_IMPORT_COMPLETED and SNAPSHOT_REGENERATED events over SSE."""
        db_state = await SyncRepository.get_latest_db_state(session)
        
        evt = await SyncManager.publish_event(
            event_type="ERP_IMPORT_COMPLETED",
            snapshot_version=db_state["snapshot_version"],
            details={"records_imported": imported_records or db_state["total_records"]}
        )

        await SyncManager.publish_event(
            event_type="SNAPSHOT_REGENERATED",
            snapshot_version=db_state["snapshot_version"],
            details={"status": "REPOPULATED"}
        )
        return evt
