"""
Operational Widgets Service Layer
Workstream 2.10 Service
"""

import time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.widgets.operational_widgets.repository import OperationalWidgetsRepository
from app.modules.site_dashboard.widgets.operational_widgets.calculations import OperationalWidgetsCalculations
from app.modules.site_dashboard.widgets.operational_widgets.dtos import OperationalWidgetsResponseDTO


class OperationalWidgetsService:
    """Orchestrates SQL queries and formats operational widgets DTO response."""

    @staticmethod
    async def get_operational_widgets(session: AsyncSession, filters: dict[str, Any]) -> OperationalWidgetsResponseDTO:
        t0 = time.perf_counter()

        raw_events = await OperationalWidgetsRepository.get_recent_operational_events(session, filters)
        dq_metrics = await OperationalWidgetsRepository.get_data_quality_metrics(session, filters)
        db_health = await OperationalWidgetsRepository.get_database_health(session, filters)
        raw_highlights = await OperationalWidgetsRepository.get_deterministic_highlights(session, filters)

        t1 = time.perf_counter()
        calc_duration_ms = (t1 - t0) * 1000.0

        health = OperationalWidgetsCalculations.build_dashboard_health(db_health, calc_duration_ms, calc_duration_ms)
        readiness = OperationalWidgetsCalculations.build_system_readiness()
        highlights = OperationalWidgetsCalculations.build_operational_highlights(raw_highlights, len(raw_events))
        events = OperationalWidgetsCalculations.build_events_feed(raw_events)
        data_quality = OperationalWidgetsCalculations.build_data_quality(dq_metrics)

        return OperationalWidgetsResponseDTO(
            dashboard_health=health,
            readiness=readiness,
            highlights=highlights,
            events=events,
            data_quality=data_quality,
        )
