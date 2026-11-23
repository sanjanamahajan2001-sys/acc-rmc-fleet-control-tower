from typing import Optional, Union, Dict, Any
from app.modules.operational_dashboard.widgets.kpis.dtos import (
    KPICardItemDTO,
    KPIStatusEnum,
    AvailabilityEnum,
)
from app.modules.operational_dashboard.widgets.kpis.services import BaseKPIEngine


class TotalDispatchesEngine(BaseKPIEngine):
    """
    Engine for KPI 5 — Total Dispatches & Volume.
    Calculates total count of dispatches under active global filters:
    - Total Dispatches = COUNT(Dispatch.id)
    - total_volume_m3 = None (SOURCE_UNAVAILABLE per Section 2.5 of Product Decision Record)
    - SLA Target = None (Target: N/A, Volume: N/A)
    - Status = NEUTRAL
    - Availability = AVAILABLE when total_count is measured (including valid zero count),
      or NO_OBSERVATIONS when count is 0 and scope has zero observations.
    """

    def calculate(
        self,
        total_count: Optional[int] = None,
    ) -> KPICardItemDTO:
        if total_count is None:
            return KPICardItemDTO(
                key="total_dispatches",
                label="Total Dispatches",
                current_value=None,
                unit="Trips",
                target=None,
                variance=None,
                total_volume_m3=None,
                status=KPIStatusEnum.NEUTRAL,
                availability=AvailabilityEnum.NO_OBSERVATIONS,
            )

        return KPICardItemDTO(
            key="total_dispatches",
            label="Total Dispatches",
            current_value=float(total_count),
            unit="Trips",
            target=None,
            variance=None,
            total_volume_m3=None,
            status=KPIStatusEnum.NEUTRAL,
            availability=AvailabilityEnum.AVAILABLE,
        )
