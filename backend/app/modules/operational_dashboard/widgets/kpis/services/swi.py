from typing import Optional, Union, Dict, Any, List
from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.services import BaseKPIEngine
from app.modules.operational_dashboard.widgets.kpis.repository import SWIMetrics


class SWIEngine(BaseKPIEngine):
    """
    Engine for KPI 2 — Site Waiting Index (SWI).
    Calculates SWI index based on holding and retention penalties:
    - SWI = max(0.0, 100.0 - (SUM(max(0, holding - 20.0)) + SUM(max(0, retention - 10.0))) / (Total Trips * 30.0) * 100.0)
    - Holding threshold SLA = 20.0 minutes
    - Retention threshold SLA = 10.0 minutes
    - Target SLA = 75.0 / 100
    - OPTIMAL: >= 75.0
    - WARNING: >= 60.0 and < 75.0
    - CRITICAL: < 60.0
    - Zero observations: current_value = None, availability = NO_OBSERVATIONS, status = NEUTRAL, variance = None
    """

    TARGET_SLA: float = 75.0
    HOLDING_THRESHOLD_MINS: float = 20.0
    RETENTION_THRESHOLD_MINS: float = 10.0
    MAX_PENALTY_PER_TRIP: float = 30.0

    def calculate(
        self,
        observations: Optional[Union[SWIMetrics, List[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> KPICardItemDTO:
        if observations is None:
            return KPICardItemDTO(
                key="swi",
                label="Site Waiting Index",
                current_value=None,
                unit="/100",
                target=self.TARGET_SLA,
                variance=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.NO_OBSERVATIONS,
            )

        total_trips = 0
        holding_pen_sum = 0.0
        retention_pen_sum = 0.0

        if isinstance(observations, SWIMetrics):
            total_trips = observations.total_trips
            holding_pen_sum = observations.holding_penalty_sum
            retention_pen_sum = observations.retention_penalty_sum
        elif isinstance(observations, list):
            total_trips = len(observations)
            for obs in observations:
                h = obs.get("t2a_holding_mins")
                r = obs.get("t2c_retention_mins")
                if h is not None and h > self.HOLDING_THRESHOLD_MINS:
                    holding_pen_sum += (h - self.HOLDING_THRESHOLD_MINS)
                if r is not None and r > self.RETENTION_THRESHOLD_MINS:
                    retention_pen_sum += (r - self.RETENTION_THRESHOLD_MINS)
        elif isinstance(observations, dict):
            total_trips = observations.get("total_trips", 0)
            holding_pen_sum = observations.get("holding_penalty_sum", 0.0)
            retention_pen_sum = observations.get("retention_penalty_sum", 0.0)

        if total_trips <= 0:
            return KPICardItemDTO(
                key="swi",
                label="Site Waiting Index",
                current_value=None,
                unit="/100",
                target=self.TARGET_SLA,
                variance=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.NO_OBSERVATIONS,
            )

        max_possible_penalty = total_trips * self.MAX_PENALTY_PER_TRIP
        total_penalty = holding_pen_sum + retention_pen_sum

        if max_possible_penalty <= 0:
            raw_swi = 100.0
        else:
            penalty_ratio = total_penalty / max_possible_penalty
            raw_swi = max(0.0, 100.0 - (penalty_ratio * 100.0))

        swi_val = round(raw_swi, 1)
        variance_val = round(swi_val - self.TARGET_SLA, 1)

        if swi_val >= self.TARGET_SLA:
            status_enum = KPIStatusEnum.OPTIMAL
        elif swi_val >= 60.0:
            status_enum = KPIStatusEnum.WARNING
        else:
            status_enum = KPIStatusEnum.CRITICAL

        return KPICardItemDTO(
            key="swi",
            label="Site Waiting Index",
            current_value=swi_val,
            unit="/100",
            target=self.TARGET_SLA,
            variance=variance_val,
            status=status_enum,
            availability=AvailabilityEnum.AVAILABLE,
        )
