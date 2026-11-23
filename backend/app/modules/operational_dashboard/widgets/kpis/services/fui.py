from typing import Optional, Union, Dict, Any, List
from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.services import BaseKPIEngine
from app.modules.operational_dashboard.widgets.kpis.repository import FUIMetrics


class FUIEngine(BaseKPIEngine):
    """
    Engine for KPI 4 — Fleet Utilization Index (FUI).
    Calculates percentage of active fleet vehicles utilized relative to registered plant fleet denominator:
    - FUI = min(100.0, (active_vehicles / registered_fleet_denominator) * 100.0)
    - Target SLA = 70.0 / 100
    - OPTIMAL: >= 70.0
    - WARNING: >= 50.0 and < 70.0
    - CRITICAL: < 50.0
    - Zero active vehicles or zero denominator: current_value = 0.0, status = CRITICAL, availability = AVAILABLE
    """

    TARGET_SLA: float = 70.0

    def calculate(
        self,
        metrics: Optional[Union[FUIMetrics, Dict[str, Any]]] = None,
    ) -> KPICardItemDTO:
        if metrics is None:
            return KPICardItemDTO(
                key="fui",
                label="Fleet Utilization Index",
                current_value=0.0,
                unit="/100",
                target=self.TARGET_SLA,
                variance=-70.0,
                status=KPIStatusEnum.CRITICAL,
                availability=AvailabilityEnum.AVAILABLE,
            )

        if isinstance(metrics, FUIMetrics):
            active_veh = metrics.active_vehicles
            reg_fleet = metrics.registered_fleet_denominator
        elif isinstance(metrics, dict):
            active_veh = metrics.get("active_vehicles", 0)
            reg_fleet = metrics.get("registered_fleet_denominator", 0)
        else:
            active_veh = 0
            reg_fleet = 0

        # Boundary: Zero registered fleet denominator or zero active vehicles -> 0.0 CRITICAL
        if reg_fleet <= 0 or active_veh <= 0:
            return KPICardItemDTO(
                key="fui",
                label="Fleet Utilization Index",
                current_value=0.0,
                unit="/100",
                target=self.TARGET_SLA,
                variance=-70.0,
                status=KPIStatusEnum.CRITICAL,
                availability=AvailabilityEnum.AVAILABLE,
            )

        raw_fui = min(100.0, (active_veh / reg_fleet) * 100.0)
        fui_val = round(raw_fui, 1)
        variance_val = round(fui_val - self.TARGET_SLA, 1)

        if fui_val >= self.TARGET_SLA:
            status_enum = KPIStatusEnum.OPTIMAL
        elif fui_val >= 50.0:
            status_enum = KPIStatusEnum.WARNING
        else:
            status_enum = KPIStatusEnum.CRITICAL

        return KPICardItemDTO(
            key="fui",
            label="Fleet Utilization Index",
            current_value=fui_val,
            unit="/100",
            target=self.TARGET_SLA,
            variance=variance_val,
            status=status_enum,
            availability=AvailabilityEnum.AVAILABLE,
        )
