"""
TM Queue Timeline Subsystem Service Orchestrator
Workstream 2.4 Service Layer
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.dto.canonical_dtos import DashboardTimelineDTO
from app.modules.site_dashboard.widgets.timeline.repository import TimelineRepository
from app.modules.site_dashboard.widgets.timeline.calculations import TimelineCalculations


class TimelineService:
    """Orchestrates SQL Queries and Timeline Phase Segmentations."""

    @staticmethod
    async def compute_timeline(session: AsyncSession, filters: dict[str, Any]) -> DashboardTimelineDTO:
        dispatches = await TimelineRepository.get_filtered_dispatches(session, filters)
        items = TimelineCalculations.build_timeline_items(dispatches)

        first_unloading = items[0].unloading_start if items else "09:40 AM"

        return DashboardTimelineDTO(
            first_unloading_time=first_unloading,
            tm_timelines=items,
        )
