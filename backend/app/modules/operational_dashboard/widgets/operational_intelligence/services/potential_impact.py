from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    PotentialImpactResponseDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawPotentialImpactObservation,
)


class PotentialImpactEngine:
    """Business Engine calculating Potential Impact of Better Planning metrics (WS-03.5 Phase 2)."""

    REDUCTION_PCT: float = 20.0  # Approved 20% target reduction parameter
    TRIPS_PER_HOUR_FACTOR: float = 0.8  # Approved fixed global business standard parameter (0.8 trips/hr)

    @classmethod
    async def evaluate_impact(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> PotentialImpactResponseDTO:
        obs: RawPotentialImpactObservation = (
            await OperationalIntelligenceRepository.get_potential_impact_metrics(
                session, filters
            )
        )

        if obs.total_dispatches == 0:
            return PotentialImpactResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data={
                    "holding_impact": {
                        "reduction_pct": cls.REDUCTION_PCT,
                        "saved_hours_total": 0.0,
                        "trips_unlocked": 0,
                    },
                    "retention_impact": {
                        "reduction_pct": cls.REDUCTION_PCT,
                        "saved_hours_total": 0.0,
                        "trips_unlocked": 0,
                    },
                    "total_impact": {
                        "saved_hours_total": 0.0,
                        "total_trips_unlocked": 0,
                    },
                },
                filters=filters,
            )

        # 1. Calculate raw saved hours for holding & retention
        holding_sav_hrs = (obs.holding_penalty_mins * (cls.REDUCTION_PCT / 100.0)) / 60.0
        retention_sav_hrs = (obs.retention_penalty_mins * (cls.REDUCTION_PCT / 100.0)) / 60.0

        # 2. Component-level trip conversion using fixed 0.8 factor
        holding_trips = round(holding_sav_hrs * cls.TRIPS_PER_HOUR_FACTOR)
        retention_trips = round(retention_sav_hrs * cls.TRIPS_PER_HOUR_FACTOR)

        # 3. Sum for total impact
        total_sav_hrs = holding_sav_hrs + retention_sav_hrs
        total_trips = holding_trips + retention_trips

        return PotentialImpactResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data={
                "holding_impact": {
                    "reduction_pct": cls.REDUCTION_PCT,
                    "saved_hours_total": round(holding_sav_hrs, 1),
                    "trips_unlocked": holding_trips,
                },
                "retention_impact": {
                    "reduction_pct": cls.REDUCTION_PCT,
                    "saved_hours_total": round(retention_sav_hrs, 1),
                    "trips_unlocked": retention_trips,
                },
                "total_impact": {
                    "saved_hours_total": round(total_sav_hrs, 1),
                    "total_trips_unlocked": total_trips,
                },
            },
            filters=filters,
        )
