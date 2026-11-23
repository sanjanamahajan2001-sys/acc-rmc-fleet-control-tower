from typing import Dict, Any, List
from datetime import datetime, time, timedelta
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    OverlapSiteDTO,
    OverlapHeatmapResponseDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawDispatchIntervalObservation,
)


class EventType:
    EXIT = -1
    ENTRY = 1


def parse_to_minutes(time_val: Any) -> float:
    """Parses time_in / time_out value (datetime, time object, or 'HH:MM:SS' string) into minutes from midnight."""
    if isinstance(time_val, time):
        return time_val.hour * 60.0 + time_val.minute + time_val.second / 60.0
    if isinstance(time_val, datetime):
        return time_val.hour * 60.0 + time_val.minute + time_val.second / 60.0
    if isinstance(time_val, str):
        parts = time_val.split(":")
        if len(parts) >= 2:
            hrs = float(parts[0])
            mins = float(parts[1])
            secs = float(parts[2]) if len(parts) > 2 else 0.0
            return hrs * 60.0 + mins + secs / 60.0
    raise ValueError(f"Cannot parse time to minutes from value {time_val!r} of type {type(time_val)}")


class OverlapHeatmapEngine:
    """Authoritative Business Calculation Engine for Widget 2: Overlap Heat Map ('Avg TMs Standing Together')."""

    @classmethod
    async def get_overlap_heatmap(
        cls, session: AsyncSession, filters: Dict[str, Any], limit: int | None = 10
    ) -> OverlapHeatmapResponseDTO:
        """Queries raw dispatch intervals, performs time-sweep concurrency analysis per customer/site partition,
        calculates overlap metrics, ranks sites deterministically, and returns OverlapHeatmapResponseDTO.
        """
        intervals = await OperationalIntelligenceRepository.get_overlap_heatmap_observations(
            session=session, filters=filters
        )

        if not intervals:
            return OverlapHeatmapResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                total_sites=0,
                data=[],
                filters=filters,
            )

        # 1. Partition intervals by customer/site code (customer_code)
        partitioned_intervals: Dict[str, List[RawDispatchIntervalObservation]] = defaultdict(list)
        customer_names: Dict[str, str] = {}
        for obs in intervals:
            partitioned_intervals[obs.customer_code].append(obs)
            if obs.customer_code not in customer_names:
                customer_names[obs.customer_code] = obs.customer_code

        site_dtos: List[OverlapSiteDTO] = []

        # 2. Perform time-sweep concurrency analysis per customer/site partition
        for cust_code, site_intervals in partitioned_intervals.items():
            if not site_intervals:
                continue

            events: List[tuple[float, int]] = []
            valid_trips = len(site_intervals)

            for obs in site_intervals:
                try:
                    start_m = parse_to_minutes(obs.time_in)
                    end_m = parse_to_minutes(obs.time_out)
                    if end_m < start_m:
                        end_m += 24.0 * 60.0  # Handle overnight wrap-around
                except Exception:
                    continue

                events.append((start_m, EventType.ENTRY))
                events.append((end_m, EventType.EXIT))

            if not events:
                continue

            # Sort events by timestamp; EXIT (-1) before ENTRY (1) at ties to avoid artificial overlap spikes
            events.sort(key=lambda x: (x[0], x[1]))

            peak_tms = 0
            current_tms = 0
            prev_time = events[0][0]
            weighted_tm_minutes = 0.0

            for event_time, event_type in events:
                duration = event_time - prev_time
                if duration > 0 and current_tms > 0:
                    if current_tms >= 2:
                        weighted_tm_minutes += duration * current_tms

                current_tms += event_type
                if current_tms > peak_tms:
                    peak_tms = current_tms

                prev_time = event_time

            total_overlap_hours = weighted_tm_minutes / 60.0
            avg_tms_standing_together = (
                weighted_tm_minutes / (valid_trips * 1.0) if valid_trips > 0 else 0.0
            )

            site_dtos.append(
                OverlapSiteDTO(
                    site_id=cust_code,
                    site_name=customer_names.get(cust_code, cust_code),
                    rank=0,
                    total_trips=valid_trips,
                    peak_tms_together=peak_tms,
                    avg_tms_standing_together=round(avg_tms_standing_together, 1),
                    overlap_hours=round(total_overlap_hours, 1),
                    weighted_tm_minutes=round(weighted_tm_minutes, 1),
                )
            )

        if not site_dtos:
            return OverlapHeatmapResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                total_sites=0,
                data=[],
                filters=filters,
            )

        site_dtos.sort(
            key=lambda s: (-s.weighted_tm_minutes, -s.overlap_hours, -s.total_trips, s.site_id)
        )

        total_sites_count = len(site_dtos)
        target_dtos = site_dtos[:limit] if limit is not None else site_dtos

        ranked_dtos: List[OverlapSiteDTO] = []
        for rank, dto in enumerate(target_dtos, 1):
            ranked_dtos.append(
                OverlapSiteDTO(
                    site_id=dto.site_id,
                    site_name=dto.site_name,
                    rank=rank,
                    total_trips=dto.total_trips,
                    peak_tms_together=dto.peak_tms_together,
                    avg_tms_standing_together=dto.avg_tms_standing_together,
                    overlap_hours=dto.overlap_hours,
                    weighted_tm_minutes=dto.weighted_tm_minutes,
                )
            )

        return OverlapHeatmapResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            total_sites=total_sites_count,
            data=ranked_dtos,
            filters=filters,
        )
