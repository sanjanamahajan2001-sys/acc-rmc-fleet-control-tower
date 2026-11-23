"""
WS-08.3 Timeline Replay Business Service.
Orchestrates scope validation, repository data retrieval, and TimelineReplayEngine invocation.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecordNotFoundError
from app.modules.operational_dashboard.widgets.timeline_replay.repository import TimelineReplayRepository
from app.modules.operational_dashboard.widgets.timeline_replay.services.timeline_engine import TimelineReplayEngine
from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    DispatchReplayListItemDTO,
    DispatchReplayListResponseDTO,
    DispatchTimelineReplayDetailDTO,
)


class TimelineReplayService:
    """
    Service Layer for WS-08.3 Timeline Replay.
    Handles input validation, scope enforcement, database query orchestration,
    and delegates lifecycle timeline calculation to WS-08.2 TimelineReplayEngine.
    """

    @classmethod
    async def list_replay_dispatches(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DispatchReplayListResponseDTO:
        """
        Lists dispatches matching operational scope with server-side pagination.
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        elif page_size > 100:
            page_size = 100

        dispatch_items, total_count = await TimelineReplayRepository.list_replay_dispatches(
            session=session,
            plant_id=plant_id,
            customer_id=customer_id,
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
        )

        dtos = [
            DispatchReplayListItemDTO(
                dispatch_id=item["dispatch_id"],
                dispatch_number=item["dispatch_number"],
                plant_id=item["plant_id"],
                customer_id=item["customer_id"],
                vehicle_id=item["vehicle_id"],
                dispatch_date=item["dispatch_date"],
                status=item["status"],
                has_telemetry=item["has_telemetry"],
            )
            for item in dispatch_items
        ]

        return DispatchReplayListResponseDTO(
            items=dtos,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    @classmethod
    async def get_dispatch_timeline_detail(
        cls,
        session: AsyncSession,
        dispatch_id: UUID,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
    ) -> DispatchTimelineReplayDetailDTO:
        """
        Retrieves authoritative timeline detail for a single dispatch.
        Enforces strict scope & dataset isolation. Raises RecordNotFoundError (404) on scope mismatch.
        Delegates lifecycle calculation to certified WS-08.2 TimelineReplayEngine.
        """
        result = await TimelineReplayRepository.get_dispatch_detail_data(
            session=session,
            dispatch_id=dispatch_id,
            plant_id=plant_id,
            customer_id=customer_id,
            dataset_id=dataset_id,
        )

        if not result:
            raise RecordNotFoundError(
                message=f"Dispatch '{dispatch_id}' not found under active plant/customer/dataset scope.",
                details={"resource_type": "DispatchTimelineReplay", "resource_id": str(dispatch_id)}
            )

        dispatch_dict, telemetry_dict, plant_dict, site_dict, alert_count = result

        # Delegate lifecycle event calculations to certified WS-08.2 engine
        dto = TimelineReplayEngine.calculate_dispatch_timeline(
            dispatch=dispatch_dict,
            telemetry=telemetry_dict,
            plant=plant_dict,
            site=site_dict,
            correlated_alert_count=alert_count,
        )

        return dto
