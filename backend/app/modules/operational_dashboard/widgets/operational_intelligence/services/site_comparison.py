from typing import Dict, Any, List
from datetime import datetime, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawSiteComparisonObservation,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    SiteComparisonDTO,
    SiteComparisonResponseDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.overlap_heatmap import parse_to_minutes


class SiteComparisonEngine:

    """Business Calculation Engine for WS-04 — Site Comparison & Benchmarking."""

    @staticmethod
    def classify_status(das_score: float) -> str:
        """Classifies site operational status based on Dispatch Accuracy Score."""
        if das_score >= 90.0:
            return "Optimal"
        elif das_score >= 70.0:
            return "Good"
        elif das_score >= 50.0:
            return "Warning"
        else:
            return "Critical"

    @classmethod
    async def _calculate_max_queue_for_scope(
        cls, session: AsyncSession, plant_id: str, customer_id: str, dataset_type: str
    ) -> int:
        """Calculates exact instantaneous peak concurrent TMs (max_queue_tms) for a given scope partition."""
        scope_filters = {
            'plant_id': plant_id,
            'customer_id': customer_id,
            'dataset_type': dataset_type,
        }
        intervals = await OperationalIntelligenceRepository.get_overlap_heatmap_observations(
            session=session, filters=scope_filters
        )
        if not intervals:
            return 0

        # Query dispatch_date for qualifying dispatches to perform accurate multi-day time-sweep
        from sqlalchemy import select
        from app.modules.erp.models import Dispatch
        stmt = select(Dispatch.id, Dispatch.dispatch_date).where(
            Dispatch.id.in_([obs.dispatch_id for obs in intervals])
        )
        res = await session.execute(stmt)
        dispatch_dates = {r.id: r.dispatch_date for r in res.all()}

        events = []
        for obs in intervals:
            try:
                tout_m = parse_to_minutes(obs.time_out)
                tin_m = parse_to_minutes(obs.time_in)
                disp_date = dispatch_dates.get(obs.dispatch_id)
                base_date = disp_date.date() if disp_date else datetime(2025, 1, 1).date()

                dep_dt = datetime.combine(base_date, time(int(tout_m // 60), int(tout_m % 60)))
                ret_dt = datetime.combine(base_date, time(int(tin_m // 60), int(tin_m % 60)))
                if tin_m < tout_m:
                    ret_dt += timedelta(days=1)

                events.append((dep_dt.timestamp(), 1))
                events.append((ret_dt.timestamp(), -1))
            except Exception:
                continue

        # Sort deterministically: timestamp ASC, EXIT (-1) before ENTRY (+1)
        events.sort(key=lambda x: (x[0], x[1]))
        curr_tms = 0
        peak_tms = 0
        for ts, event_type in events:
            curr_tms += event_type
            if curr_tms > peak_tms:
                peak_tms = curr_tms

        return peak_tms

    @classmethod
    async def get_site_comparison(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> SiteComparisonResponseDTO:
        raw_obs: List[RawSiteComparisonObservation] = (
            await OperationalIntelligenceRepository.get_site_comparison_observations(
                session=session, filters=filters
            )
        )

        if not raw_obs:
            return SiteComparisonResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=[],
                filters=filters,
            )

        active_customer_id = filters.get("customer_id", "ALL")
        active_dataset_type = filters.get("dataset_type", "REAL_ONLY")

        comparison_list: List[Dict[str, Any]] = []
        for obs in raw_obs:
            dispatches = obs.dispatches
            das_score = round((obs.accurate_count / dispatches) * 100.0, 1) if dispatches > 0 else 0.0
            status_label = cls.classify_status(das_score)

            # Dynamically compute max_queue_tms using time-sweep concurrency engine for specific scope
            max_queue = await cls._calculate_max_queue_for_scope(
                session=session,
                plant_id=obs.site_code,
                customer_id=active_customer_id,
                dataset_type=active_dataset_type,
            )

            comparison_list.append(
                {
                    "site_code": obs.site_code,
                    "site_name": obs.site_name,
                    "dispatches": dispatches,
                    "volume_cum": round(obs.volume_cum, 1),
                    "avg_holding_mins": round(obs.avg_holding_mins, 1),
                    "avg_retention_mins": round(obs.avg_retention_mins, 1),
                    "max_queue_tms": max_queue,
                    "dispatch_accuracy": das_score,
                    "status": status_label,
                }
            )

        # Deterministic 3-tier ranking: dispatches DESC, volume_cum DESC, site_code ASC
        sorted_sites = sorted(
            comparison_list,
            key=lambda x: (-x["dispatches"], -x["volume_cum"], x["site_code"]),
        )

        site_dtos: List[SiteComparisonDTO] = [
            SiteComparisonDTO(
                rank=idx + 1,
                site_code=s["site_code"],
                site_name=s["site_name"],
                dispatches=s["dispatches"],
                volume_cum=s["volume_cum"],
                avg_holding_mins=s["avg_holding_mins"],
                avg_retention_mins=s["avg_retention_mins"],
                max_queue_tms=s["max_queue_tms"],
                dispatch_accuracy=s["dispatch_accuracy"],
                status=s["status"],
            )
            for idx, s in enumerate(sorted_sites)
        ]

        return SiteComparisonResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=site_dtos,
            filters=filters,
        )
