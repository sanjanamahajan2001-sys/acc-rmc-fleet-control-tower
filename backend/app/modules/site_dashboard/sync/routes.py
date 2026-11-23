"""
Workstream 2.11 Synchronization Router & API Endpoint Definitions
Exposes /sync/status, /sync/refresh, /sync/notify-reset, /sync/notify-import, and /sync/events SSE stream.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.site_dashboard.sync.service import SyncService
from app.modules.site_dashboard.sync.sync_manager import SyncManager
from app.modules.site_dashboard.sync.dtos import SyncStatusDTO, RefreshResultDTO, SyncEventDTO


sync_router = APIRouter(prefix="/site-dashboard/sync", tags=["Site Dashboard Sync"])


@sync_router.get("/status", response_model=dict)
async def get_sync_status(session: AsyncSession = Depends(get_db_session)):
    """Returns current real-time dashboard synchronization status."""
    data = await SyncService.get_sync_status(session)
    return {"success": True, "data": data.model_dump()}


@sync_router.post("/refresh", response_model=dict)
async def trigger_manual_refresh(session: AsyncSession = Depends(get_db_session)):
    """Triggers an explicit manual snapshot refresh and publishes SNAPSHOT_REGENERATED over SSE."""
    data = await SyncService.trigger_manual_refresh(session)
    return {"success": True, "data": data.model_dump()}


@sync_router.post("/notify-reset", response_model=dict)
async def notify_erp_reset(session: AsyncSession = Depends(get_db_session)):
    """Publishes ERP_RESET_COMPLETED and SNAPSHOT_INVALIDATED events across connected operators."""
    data = await SyncService.notify_erp_reset(session)
    return {"success": True, "data": data.model_dump()}


@sync_router.post("/notify-import", response_model=dict)
async def notify_erp_import(
    records: int = Query(0, description="Total records imported"),
    session: AsyncSession = Depends(get_db_session)
):
    """Publishes ERP_IMPORT_COMPLETED and SNAPSHOT_REGENERATED events across connected operators."""
    data = await SyncService.notify_erp_import(session, records)
    return {"success": True, "data": data.model_dump()}


@sync_router.get("/events")
async def stream_sync_events():
    """Server-Sent Events (SSE) stream endpoint publishing real-time synchronization notifications."""
    return StreamingResponse(
        SyncManager.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
