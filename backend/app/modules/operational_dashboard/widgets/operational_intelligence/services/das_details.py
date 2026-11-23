from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    DASDetailsResponseDTO,
    DASDetailRowDTO,
    DASSummaryDTO,
    DASBucketBreakdownDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawDASDetailObservation,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_overview import DASOverviewEngine


class DASDetailsEngine:
    """
    Authoritative Business Logic Engine for WS-03.4 Dispatch Accuracy Score (DAS) Details.
    Evaluates customer-level DAS accuracy score breakdown and 3-bucket delay classification.
    Reconciles 100% with DASOverviewEngine aggregate metrics.
    """

    @classmethod
    async def evaluate_details(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> DASDetailsResponseDTO:
        # 1. Fetch overview metrics to guarantee 100% summary reconciliation
        overview_dto = await DASOverviewEngine.evaluate_overview(session, filters)

        if overview_dto.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS:
            return DASDetailsResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                total_customers=0,
                summary=overview_dto.summary,
                buckets=overview_dto.buckets,
                data=[],
                filters=filters,
            )

        # 2. Fetch customer-level SQL aggregated observations
        raw_obs: List[RawDASDetailObservation] = await OperationalIntelligenceRepository.get_das_detail_observations(
            session, filters
        )

        detail_rows: List[DASDetailRowDTO] = []
        for obs in raw_obs:
            if obs.total_dispatches <= 0:
                continue

            das_score = round((obs.accurate_count / obs.total_dispatches) * 100.0, 1)
            within_20m_pct = round((obs.accurate_count / obs.total_dispatches) * 100.0, 1)
            moderate_pct = round((obs.moderate_count / obs.total_dispatches) * 100.0, 1)
            critical_pct = round((obs.critical_count / obs.total_dispatches) * 100.0, 1)

            if das_score >= DASOverviewEngine.TARGET_SLA:
                operational_status = "OPTIMAL"
            elif das_score >= 80.0:
                operational_status = "WARNING"
            else:
                operational_status = "CRITICAL"

            detail_rows.append(
                DASDetailRowDTO(
                    customer_id=obs.customer_code,
                    customer_name=obs.customer_name,
                    rank=0,
                    total_dispatches=obs.total_dispatches,
                    accurate_count=obs.accurate_count,
                    moderate_count=obs.moderate_count,
                    critical_count=obs.critical_count,
                    das_score=das_score,
                    within_20m_pct=within_20m_pct,
                    moderate_pct=moderate_pct,
                    critical_pct=critical_pct,
                    operational_status=operational_status,
                )
            )

        # Deterministic Ranking: das_score ASC (intervention first), total_dispatches DESC, customer_id ASC
        detail_rows.sort(key=lambda r: (r.das_score, -r.total_dispatches, r.customer_id))

        ranked_rows: List[DASDetailRowDTO] = []
        for rank, row in enumerate(detail_rows, 1):
            ranked_rows.append(
                DASDetailRowDTO(
                    customer_id=row.customer_id,
                    customer_name=row.customer_name,
                    rank=rank,
                    total_dispatches=row.total_dispatches,
                    accurate_count=row.accurate_count,
                    moderate_count=row.moderate_count,
                    critical_count=row.critical_count,
                    das_score=row.das_score,
                    within_20m_pct=row.within_20m_pct,
                    moderate_pct=row.moderate_pct,
                    critical_pct=row.critical_pct,
                    operational_status=row.operational_status,
                )
            )

        return DASDetailsResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            total_customers=len(ranked_rows),
            summary=overview_dto.summary,
            buckets=overview_dto.buckets,
            data=ranked_rows,
            filters=filters,
        )
