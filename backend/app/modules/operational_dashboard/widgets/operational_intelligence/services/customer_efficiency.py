from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    CustomerEfficiencyDTO,
    CustomerEfficiencyResponseDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.problem_customers import (
    ProblemCustomersEngine,
)


class CustomerEfficiencyEngine:
    """Authoritative Business Engine for WS-03.6 Widget: Customer Efficiency Index (CEI)."""

    @classmethod
    def classify_grade(cls, cei_score: float) -> str:
        """Classifies CEI score into certified production grade labels.
        CEI >= 70.0 -> Good
        40.0 <= CEI < 70.0 -> Needs Improvement
        CEI < 40.0 -> Critical
        """
        if cei_score >= 70.0:
            return "Good"
        elif cei_score >= 40.0:
            return "Needs Improvement"
        else:
            return "Critical"

    @classmethod
    async def get_customer_efficiency(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> CustomerEfficiencyResponseDTO:
        """Evaluates customer efficiency index, applies deterministic ranking (cei_score ASC, total_trips DESC, customer_code ASC),
        and returns the certified DTO response.
        """
        raw_obs = await OperationalIntelligenceRepository.get_customer_efficiency_observations(
            session=session, filters=filters
        )

        if not raw_obs:
            return CustomerEfficiencyResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=[],
                filters=filters,
            )

        evaluated_customers = []
        for obs in raw_obs:
            cei_val = ProblemCustomersEngine.calculate_cei(
                obs.holding_penalty_mins, obs.retention_penalty_mins, obs.total_trips
            )
            grade_val = cls.classify_grade(cei_val)

            evaluated_customers.append({
                "customer_code": obs.customer_code,
                "customer_name": obs.customer_name or obs.customer_code,
                "total_trips": obs.total_trips,
                "holding_penalty_mins": obs.holding_penalty_mins,
                "retention_penalty_mins": obs.retention_penalty_mins,
                "cei_score": cei_val,
                "grade": grade_val,
                "trend": "FLAT",
            })

        # Deterministic Ranking: cei_score ASC, total_trips DESC, customer_code ASC
        sorted_customers = sorted(
            evaluated_customers,
            key=lambda x: (x["cei_score"], -x["total_trips"], x["customer_code"])
        )

        customer_dtos: List[CustomerEfficiencyDTO] = []
        for rank_idx, item in enumerate(sorted_customers, 1):
            customer_dtos.append(
                CustomerEfficiencyDTO(
                    rank=rank_idx,
                    customer_id=item["customer_code"],
                    customer_name=item["customer_name"],
                    cei_score=item["cei_score"],
                    grade=item["grade"],
                    trend=item["trend"],
                    total_trips=item["total_trips"],
                    holding_penalty_mins=round(item["holding_penalty_mins"], 1),
                    retention_penalty_mins=round(item["retention_penalty_mins"], 1),
                )
            )

        return CustomerEfficiencyResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=customer_dtos,
            filters=filters,
        )
