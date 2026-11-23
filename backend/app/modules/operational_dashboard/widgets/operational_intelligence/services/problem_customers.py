from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    ProblemCustomerDTO,
    ProblemCustomerListResponseDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawProblemCustomerObservation,
)


class ProblemCustomersEngine:
    """Authoritative Business Calculation Engine for Widget 1: Top 10 Problem Customers."""

    @classmethod
    def calculate_cei(cls, holding_pen_mins: float, retention_pen_mins: float, total_trips: int) -> float:
        """Calculates Customer Efficiency Index (CEI) using raw unrounded penalty minutes to preserve maximum precision.
        CEI = MAX(0.0, 100.0 - (((holding_pen_mins + retention_pen_mins) / (total_trips * 30.0)) * 100.0))
        """
        if total_trips <= 0:
            return 0.0
        tot_pen_mins = holding_pen_mins + retention_pen_mins
        max_alloc_mins = total_trips * 30.0
        penalty_ratio = (tot_pen_mins / max_alloc_mins) * 100.0
        cei = max(0.0, 100.0 - penalty_ratio)
        return round(cei, 1)

    @classmethod
    async def get_top_problem_customers(
        cls, session: AsyncSession, filters: Dict[str, Any], limit: int | None = None
    ) -> ProblemCustomerListResponseDTO:
        """Queries raw observations, evaluates lost hours and CEI, ranks customers, and returns DTO."""
        raw_obs = await OperationalIntelligenceRepository.get_problem_customer_observations(
            session=session, filters=filters
        )

        if not raw_obs:
            return ProblemCustomerListResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                total_count=0,
                data=[],
                filters=filters,
            )

        customer_dtos: List[ProblemCustomerDTO] = []
        for obs in raw_obs:
            holding_hrs = round(obs.holding_penalty_mins / 60.0, 1)
            retention_hrs = round(obs.retention_penalty_mins / 60.0, 1)
            total_lost_hrs = round((obs.holding_penalty_mins + obs.retention_penalty_mins) / 60.0, 1)
            cei_val = cls.calculate_cei(obs.holding_penalty_mins, obs.retention_penalty_mins, obs.total_trips)

            customer_dtos.append(
                ProblemCustomerDTO(
                    customer_id=obs.customer_code,
                    customer_name=obs.customer_name or obs.customer_code,
                    rank=0,
                    total_trips=obs.total_trips,
                    holding_hours=holding_hrs,
                    retention_hours=retention_hrs,
                    total_lost_hours=total_lost_hrs,
                    cei=cei_val,
                )
            )

        # Sort by total_lost_hours DESC, total_trips DESC, customer_id ASC
        customer_dtos.sort(key=lambda c: (-c.total_lost_hours, -c.total_trips, c.customer_id))

        ranked_dtos: List[ProblemCustomerDTO] = []
        subset = customer_dtos[:limit] if limit is not None else customer_dtos
        for rank, dto in enumerate(subset, 1):
            ranked_dtos.append(
                ProblemCustomerDTO(
                    customer_id=dto.customer_id,
                    customer_name=dto.customer_name,
                    rank=rank,
                    total_trips=dto.total_trips,
                    holding_hours=dto.holding_hours,
                    retention_hours=dto.retention_hours,
                    total_lost_hours=dto.total_lost_hours,
                    cei=dto.cei,
                )
            )

        return ProblemCustomerListResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            total_count=len(ranked_dtos),
            data=ranked_dtos,
            filters=filters,
        )
