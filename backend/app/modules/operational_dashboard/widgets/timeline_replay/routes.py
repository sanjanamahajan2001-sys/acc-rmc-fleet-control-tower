"""
WS-08.3 Timeline Replay FastAPI REST Router.
Provides production API endpoints for listing dispatches and retrieving authoritative digital twin timeline replay detail.
"""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.operational_dashboard.widgets.timeline_replay.service import TimelineReplayService
from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    DispatchReplayListResponseDTO,
    DispatchTimelineReplayDetailDTO,
)

router = APIRouter(prefix="/timeline-replay", tags=["Timeline Replay"])

@router.get(
    "/dispatches",
    response_model=DispatchReplayListResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="List Timeline Replay Dispatches",
    description="Returns a paginated list of dispatches available for timeline replay under active plant, customer, or dataset scope.",
)
async def list_replay_dispatches(
    plant_id: str = Query("ALL", description="Plant filter ID or ALL"),
    customer_id: str = Query("ALL", description="Customer filter ID or ALL"),
    dataset_id: Optional[str] = Query(None, description="Dataset ID filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    session: AsyncSession = Depends(get_db_session),
) -> DispatchReplayListResponseDTO:
    return await TimelineReplayService.list_replay_dispatches(
        session=session,
        plant_id=plant_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
    )

@router.get(
    "/dispatches/{dispatch_id}",
    response_model=DispatchTimelineReplayDetailDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Dispatch Timeline Replay Detail",
    description="Returns full authoritative digital twin timeline replay detail for a single dispatch with strict scope isolation.",
)
async def get_dispatch_timeline_detail(
    dispatch_id: UUID,
    plant_id: str = Query("ALL", description="Plant filter ID or ALL"),
    customer_id: str = Query("ALL", description="Customer filter ID or ALL"),
    dataset_id: Optional[str] = Query(None, description="Dataset ID filter"),
    session: AsyncSession = Depends(get_db_session),
) -> DispatchTimelineReplayDetailDTO:
    return await TimelineReplayService.get_dispatch_timeline_detail(
        session=session,
        dispatch_id=dispatch_id,
        plant_id=plant_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
    )
