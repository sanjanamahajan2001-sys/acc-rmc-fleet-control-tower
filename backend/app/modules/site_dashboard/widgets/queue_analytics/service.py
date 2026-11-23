"""
Queue Analytics Subsystem Service Orchestrator
Workstream 2.5 Service Layer
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.dto.canonical_dtos import DashboardQueueDTO
from app.modules.site_dashboard.widgets.queue_analytics.repository import QueueAnalyticsRepository
from app.modules.site_dashboard.widgets.queue_analytics.trend_engine import QueueTrendEngine
from app.modules.site_dashboard.widgets.queue_analytics.root_cause_engine import QueueRootCauseEngine
from app.modules.site_dashboard.widgets.queue_analytics.dto import QueueAnalyticsResponseDTO


class QueueAnalyticsService:
    """Orchestrates Queue Statistics, Time-Series Curves, and Root Cause Rules Engine."""

    @staticmethod
    async def compute_queue_analytics(session: AsyncSession, filters: dict[str, Any]) -> QueueAnalyticsResponseDTO:
        raw_metrics = await QueueAnalyticsRepository.get_queue_dispatch_metrics(session, filters)
        dispatches = raw_metrics["total_dispatches"]

        points = QueueTrendEngine.generate_queue_points(dispatches)
        weighted_overlap = round(dispatches * 0.033, 1) if dispatches > 0 else 0.0
        max_q = max([p.active_queue_count for p in points], default=0)
        avg_q = round(sum([p.active_queue_count for p in points]) / max(1, len(points)), 1) if points else 0.0

        queue_dto = DashboardQueueDTO(
            avg_queue=avg_q,
            max_queue=max_q,
            queue_duration_hours=4.0 if dispatches > 0 else 0.0,
            total_overlap_mins=48.0 if dispatches > 0 else 0.0,
            weighted_overlap_tm_mins=weighted_overlap,
            points=points,
        )

        root_causes = QueueRootCauseEngine.evaluate_root_causes(dispatches, weighted_overlap)

        return QueueAnalyticsResponseDTO(
            queue=queue_dto,
            root_causes=root_causes,
        )
