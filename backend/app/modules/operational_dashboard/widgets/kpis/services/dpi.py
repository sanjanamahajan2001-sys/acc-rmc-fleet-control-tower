from typing import Optional, Union, Dict, Any, List
from datetime import time, datetime
from collections import defaultdict

from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.services import BaseKPIEngine
from app.modules.operational_dashboard.widgets.kpis.repository import DPIObservation


class DPIEngine(BaseKPIEngine):
    """
    Engine for KPI 3 — Dispatch Planning Index (DPI).
    Calculates percentage of consecutive dispatch intervals per customer site that meet or exceed target cycle time:
    - Grouping key: customer_id
    - Partition sort: time_out ascending
    - First trip of each site partition is excluded from interval calculation
    - dispatch_interval = current trip time_out - previous trip time_out
    - target_interval = max(15.0 mins, t1_transit_mins + t2b_unloading_mins)
    - Compliant if dispatch_interval >= target_interval
    - Target SLA = 85.0 / 100
    - OPTIMAL: >= 85.0
    - WARNING: >= 70.0 and < 85.0
    - CRITICAL: < 70.0
    - Zero eligible intervals: current_value = None, availability = BASELINE_UNAVAILABLE, status = NEUTRAL, variance = None
    """

    TARGET_SLA: float = 85.0
    MIN_TARGET_INTERVAL_MINS: float = 15.0

    @staticmethod
    def _parse_time(val: Any) -> Optional[time]:
        if val is None:
            return None
        if isinstance(val, time):
            return val
        if isinstance(val, datetime):
            return val.time()
        if isinstance(val, str):
            try:
                parts = val.split(":")
                return time(int(parts[0]), int(parts[1]), int(float(parts[2])))
            except (ValueError, IndexError):
                return None
        return None

    @staticmethod
    def _time_to_minutes(t: time) -> float:
        return t.hour * 60.0 + t.minute + t.second / 60.0

    def calculate(self, observations: Optional[List[DPIObservation]] = None) -> KPICardItemDTO:
        if not observations:
            return KPICardItemDTO(
                key="dpi",
                label="Dispatch Planning Index",
                current_value=None,
                unit="/100",
                target=self.TARGET_SLA,
                variance=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.BASELINE_UNAVAILABLE,
            )

        # 1. Group observations by customer_id
        grouped: Dict[Any, List[DPIObservation]] = defaultdict(list)
        for obs in observations:
            if obs.customer_id is not None and obs.time_out is not None:
                grouped[obs.customer_id].append(obs)

        total_eligible_intervals = 0
        compliant_intervals = 0

        # 2. Iterate partitions and evaluate consecutive trip intervals
        for cust_id, partition in grouped.items():
            # Sort dispatches within partition by time_out ascending
            partition.sort(
                key=lambda x: self._time_to_minutes(self._parse_time(x.time_out)) if self._parse_time(x.time_out) else -1.0
            )

            for i in range(1, len(partition)):
                prev_trip = partition[i - 1]
                curr_trip = partition[i]

                prev_t = self._parse_time(prev_trip.time_out)
                curr_t = self._parse_time(curr_trip.time_out)

                t1 = curr_trip.t1_transit_mins
                t2b = curr_trip.t2b_unloading_mins

                # Strict Data Eligibility Rule
                if prev_t is None or curr_t is None or t1 is None or t2b is None:
                    continue

                curr_mins = self._time_to_minutes(curr_t)
                prev_mins = self._time_to_minutes(prev_t)
                dispatch_interval = curr_mins - prev_mins

                if dispatch_interval <= 0.0:
                    continue

                target_interval = max(self.MIN_TARGET_INTERVAL_MINS, t1 + t2b)

                total_eligible_intervals += 1
                if dispatch_interval >= target_interval:
                    compliant_intervals += 1

        # 3. Handle zero eligible intervals boundary
        if total_eligible_intervals <= 0:
            return KPICardItemDTO(
                key="dpi",
                label="Dispatch Planning Index",
                current_value=None,
                unit="/100",
                target=self.TARGET_SLA,
                variance=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.BASELINE_UNAVAILABLE,
            )

        # 4. Compute DPI ratio, variance, status
        raw_dpi = (compliant_intervals / total_eligible_intervals) * 100.0
        dpi_val = round(raw_dpi, 1)
        variance_val = round(dpi_val - self.TARGET_SLA, 1)

        if dpi_val >= self.TARGET_SLA:
            status_enum = KPIStatusEnum.OPTIMAL
        elif dpi_val >= 70.0:
            status_enum = KPIStatusEnum.WARNING
        else:
            status_enum = KPIStatusEnum.CRITICAL

        return KPICardItemDTO(
            key="dpi",
            label="Dispatch Planning Index",
            current_value=dpi_val,
            unit="/100",
            target=self.TARGET_SLA,
            variance=variance_val,
            status=status_enum,
            availability=AvailabilityEnum.AVAILABLE,
        )
