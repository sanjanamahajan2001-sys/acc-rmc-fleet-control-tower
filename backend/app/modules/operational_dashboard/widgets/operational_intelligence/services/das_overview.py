from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    DASOverviewResponseDTO,
    DASSummaryDTO,
    DASBucketBreakdownDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawDASOverviewMetrics,
)


class DASOverviewEngine:
    """
    Business logic engine for WS-03.4 Dispatch Accuracy Score (DAS) Overview.
    Calculates percentage of dispatches with site holding duration t2a_holding_mins <= 20.0 minutes,
    along with 3-bucket delay classification (Within 20m, 20-40m, >40m).

    Authoritative SLA Contract:
    - Target SLA = 90.0%
    - OPTIMAL: DAS >= 90.0%
    - WARNING: 80.0% <= DAS < 90.0%
    - CRITICAL: DAS < 80.0%
    - NO_OBSERVATIONS: total_dispatches == 0 (current_value = None, status = NEUTRAL, availability = NO_OBSERVATIONS)
    """

    TARGET_SLA: float = 90.0
    ACCURATE_THRESHOLD_MINS: float = 20.0
    MODERATE_THRESHOLD_MINS: float = 40.0

    @classmethod
    async def evaluate_overview(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> DASOverviewResponseDTO:
        metrics: RawDASOverviewMetrics = await OperationalIntelligenceRepository.get_das_overview_metrics(
            session, filters
        )

        total_cnt = metrics.total_dispatches
        accurate_cnt = metrics.accurate_count
        range_21_40_cnt = metrics.range_21_40_count
        range_41_60_cnt = metrics.range_41_60_count
        above_60_cnt = metrics.above_60_count
        moderate_cnt = metrics.moderate_count
        critical_cnt = metrics.critical_count

        # Handle NO_OBSERVATIONS honest empty state
        if total_cnt <= 0:
            summary_dto = DASSummaryDTO(
                total_dispatches=0,
                accurate_dispatches=0,
                das_score=None,
                target_sla=cls.TARGET_SLA,
                variance=None,
                operational_status="NEUTRAL",
            )
            bucket_dto = DASBucketBreakdownDTO(
                within_20m_count=0,
                within_20m_pct=0.0,
                range_21_40m_count=0,
                range_21_40m_pct=0.0,
                range_41_60m_count=0,
                range_41_60m_pct=0.0,
                above_60m_count=0,
                above_60m_pct=0.0,
                moderate_20_40m_count=0,
                moderate_20_40m_pct=0.0,
                critical_above_40m_count=0,
                critical_above_40m_pct=0.0,
            )
            return DASOverviewResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                summary=summary_dto,
                buckets=bucket_dto,
                filters=filters,
            )

        # Calculate exact percentage score & rounding to 1 decimal place
        raw_das_pct = (accurate_cnt / total_cnt) * 100.0
        das_score = round(raw_das_pct, 1)
        variance = round(das_score - cls.TARGET_SLA, 1)

        # Calculate 4-bucket and 3-bucket percentages
        within_20m_pct = round((accurate_cnt / total_cnt) * 100.0, 1)
        range_21_40m_pct = round((range_21_40_cnt / total_cnt) * 100.0, 1)
        range_41_60m_pct = round((range_41_60_cnt / total_cnt) * 100.0, 1)
        above_60m_pct = round((above_60_cnt / total_cnt) * 100.0, 1)

        moderate_pct = round((moderate_cnt / total_cnt) * 100.0, 1)
        critical_pct = round((critical_cnt / total_cnt) * 100.0, 1)

        # Authoritative status classification
        if das_score >= cls.TARGET_SLA:
            operational_status = "OPTIMAL"
        elif das_score >= 80.0:
            operational_status = "WARNING"
        else:
            operational_status = "CRITICAL"

        summary_dto = DASSummaryDTO(
            total_dispatches=total_cnt,
            accurate_dispatches=accurate_cnt,
            das_score=das_score,
            target_sla=cls.TARGET_SLA,
            variance=variance,
            operational_status=operational_status,
        )

        bucket_dto = DASBucketBreakdownDTO(
            within_20m_count=accurate_cnt,
            within_20m_pct=within_20m_pct,
            range_21_40m_count=range_21_40_cnt,
            range_21_40m_pct=range_21_40m_pct,
            range_41_60m_count=range_41_60_cnt,
            range_41_60m_pct=range_41_60m_pct,
            above_60m_count=above_60_cnt,
            above_60m_pct=above_60m_pct,
            moderate_20_40m_count=moderate_cnt,
            moderate_20_40m_pct=moderate_pct,
            critical_above_40m_count=critical_cnt,
            critical_above_40m_pct=critical_pct,
        )

        return DASOverviewResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            summary=summary_dto,
            buckets=bucket_dto,
            filters=filters,
        )
