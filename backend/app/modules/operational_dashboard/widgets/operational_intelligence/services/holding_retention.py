from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawHoldingRetentionObservation,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    HoldingRetentionTrendPointDTO,
    HoldingRetentionSummaryDTO,
    HoldingRetentionResponseDTO,
    OperationalIntelligenceStatusEnum,
)


class HoldingRetentionEngine:
    """
    Business Engine for WS-03.3 Holding & Retention Overview.
    Evaluates 24 hourly trend points and aggregate summary metrics.
    """

    HOLDING_SLA_MINS: float = 20.0
    RETENTION_SLA_MINS: float = 10.0

    @classmethod
    async def evaluate_overview(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> HoldingRetentionResponseDTO:
        observations: List[RawHoldingRetentionObservation] = (
            await OperationalIntelligenceRepository.get_holding_retention_observations(session, filters)
        )

        total_dispatches = sum(obs.total_dispatches for obs in observations)
        total_holding_pen_mins = round(sum(obs.holding_penalty_mins for obs in observations), 1)
        total_retention_pen_mins = round(sum(obs.retention_penalty_mins for obs in observations), 1)
        total_lost_hours = round((total_holding_pen_mins + total_retention_pen_mins) / 60.0, 1)

        # Empty State Protection: If 0 matching dispatches evaluated
        if total_dispatches == 0:
            return HoldingRetentionResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                summary=HoldingRetentionSummaryDTO(
                    total_dispatches=0,
                    total_holding_penalty_mins=0.0,
                    total_retention_penalty_mins=0.0,
                    total_lost_hours=0.0,
                ),
                data=[],
                filters=filters,
            )

        # Build 24 hourly trend points
        trend_points: List[HoldingRetentionTrendPointDTO] = []
        for obs in observations:
            h_pen = round(obs.holding_penalty_mins, 1)
            r_pen = round(obs.retention_penalty_mins, 1)
            lost_h = round((h_pen + r_pen) / 60.0, 2)

            trend_points.append(
                HoldingRetentionTrendPointDTO(
                    hour_label=obs.hour_label,
                    total_dispatches=obs.total_dispatches,
                    holding_penalty_mins=h_pen,
                    retention_penalty_mins=r_pen,
                    total_lost_hours=lost_h,
                )
            )

        summary = HoldingRetentionSummaryDTO(
            total_dispatches=total_dispatches,
            total_holding_penalty_mins=total_holding_pen_mins,
            total_retention_penalty_mins=total_retention_pen_mins,
            total_lost_hours=total_lost_hours,
        )

        return HoldingRetentionResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            summary=summary,
            data=trend_points,
            filters=filters,
        )
