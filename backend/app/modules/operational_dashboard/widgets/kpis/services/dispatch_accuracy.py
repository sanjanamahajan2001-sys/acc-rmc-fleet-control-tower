from typing import Optional, Union, Dict, Any
from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.services import BaseKPIEngine
from app.modules.operational_dashboard.widgets.kpis.repository import DispatchAccuracyMetrics


class DispatchAccuracyEngine(BaseKPIEngine):
    """
    Engine for KPI 1 — Dispatch Accuracy.
    Calculates percentage of dispatches with site holding duration t2a_holding_mins <= 20.0 minutes.
    - Target SLA = 90.0%
    - OPTIMAL: >= 90.0%
    - WARNING: >= 80.0% and < 90.0%
    - CRITICAL: < 80.0%
    - Zero observations: current_value = None, availability = NO_OBSERVATIONS, status = NEUTRAL, variance = None
    """

    TARGET_SLA: float = 90.0
    HOLDING_THRESHOLD_MINS: float = 20.0

    def calculate(self, observations: Optional[Union[DispatchAccuracyMetrics, Dict[str, Any]]] = None) -> KPICardItemDTO:
        if observations is None:
            return KPICardItemDTO(
                key="accuracy",
                label="Dispatch Accuracy",
                current_value=None,
                unit="%",
                target=self.TARGET_SLA,
                variance=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.NO_OBSERVATIONS,
            )

        if isinstance(observations, DispatchAccuracyMetrics):
            accurate_count = observations.accurate_count
            total_count = observations.total_count
        elif isinstance(observations, dict):
            accurate_count = observations.get("accurate_count", 0)
            total_count = observations.get("total_count", 0)
        else:
            accurate_count = 0
            total_count = 0

        if total_count <= 0:
            return KPICardItemDTO(
                key="accuracy",
                label="Dispatch Accuracy",
                current_value=None,
                unit="%",
                target=self.TARGET_SLA,
                variance=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.NO_OBSERVATIONS,
            )

        raw_pct = (accurate_count / total_count) * 100.0
        accuracy_val = round(raw_pct, 1)
        variance_val = round(accuracy_val - self.TARGET_SLA, 1)

        if accuracy_val >= self.TARGET_SLA:
            status_enum = KPIStatusEnum.OPTIMAL
        elif accuracy_val >= 80.0:
            status_enum = KPIStatusEnum.WARNING
        else:
            status_enum = KPIStatusEnum.CRITICAL

        return KPICardItemDTO(
            key="accuracy",
            label="Dispatch Accuracy",
            current_value=accuracy_val,
            unit="%",
            target=self.TARGET_SLA,
            variance=variance_val,
            status=status_enum,
            availability=AvailabilityEnum.AVAILABLE,
        )
