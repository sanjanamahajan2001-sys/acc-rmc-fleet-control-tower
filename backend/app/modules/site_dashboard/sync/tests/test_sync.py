import pytest
import time
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.sync.service import SyncService
from app.modules.site_dashboard.sync.sync_manager import SyncManager


@pytest.mark.asyncio
async def test_sync_service_and_events():
    async with AsyncSessionFactory() as session:
        t0 = time.perf_counter()
        status = await SyncService.get_sync_status(session)
        t1 = time.perf_counter()
        dur_ms = (t1 - t0) * 1000.0

        assert status is not None
        assert status.sync_status in ["SYNCHRONIZED", "REFRESHING", "LAGGING", "DISCONNECTED"]
        assert status.e_tag is not None
        assert status.snapshot_version is not None
        assert dur_ms < 100.0, f"Sync status evaluation duration {dur_ms}ms exceeds 100ms SLA"

        # Verify ERP Reset event publication
        reset_evt = await SyncService.notify_erp_reset(session)
        assert reset_evt.event_type == "ERP_RESET_COMPLETED"
        assert reset_evt.snapshot_version == "v2.11-SNAP-EMPTY"

        # Verify ERP Import event publication
        import_evt = await SyncService.notify_erp_import(session, 3532)
        assert import_evt.event_type == "ERP_IMPORT_COMPLETED"
        assert import_evt.details["records_imported"] == 3532

        # Verify Manual Refresh Execution
        refresh_res = await SyncService.trigger_manual_refresh(session)
        assert refresh_res.success is True
        assert refresh_res.duration_ms < 300.0
