"""
WS-06.3 Optimization Readiness Engine for Dispatch Optimization Control Center.
Evaluates filtered operational dataset availability, data quality, fleet availability,
and temporal feasibility to determine readiness status (READY, DEGRADED, NO_OBSERVATIONS).
"""

from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import DispatchAnalysisRepository
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationReadinessDTO,
    ReadinessStatusEnum,
    DataQualitySummaryDTO,
    OptimizationFilterParamsDTO,
)


class OptimizationReadinessEngine:
    """Business calculation engine evaluating operational dataset readiness for optimization."""

    @classmethod
    async def evaluate_readiness(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> OptimizationReadinessDTO:
        # 1. Parse filter params using shared platform contract
        plant_id = filters.get("plant_id", "ALL")
        customer_id = filters.get("customer_id", "ALL")
        dataset_type = filters.get("dataset_type", "REAL_ONLY")

        filter_dto = OptimizationFilterParamsDTO(
            plant_id=plant_id,
            customer_id=customer_id,
            dataset_type=dataset_type,
        )

        # 2. Fetch scoped dispatches via certified DispatchAnalysisRepository
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        # 3. Handle NO_OBSERVATIONS empty state
        if not dispatches:
            return OptimizationReadinessDTO(
                success=True,
                status=ReadinessStatusEnum.NO_OBSERVATIONS,
                reason_code="NO_DISPATCHES",
                message="No operational dispatches found for the selected filter scope.",
                quality_summary=DataQualitySummaryDTO(
                    total_dispatches=0,
                    active_vehicle_count=0,
                    plant_count=0,
                    customer_count=0,
                    missing_timestamp_count=0,
                    missing_vehicle_count=0,
                ),
                blocking_conditions=["NO_DISPATCHES_FOUND"],
                filters=filter_dto,
            )

        # 4. Perform Data Quality & Fleet Feasibility Inspections
        distinct_vehicles = {d["vehicle_id"] for d in dispatches if d.get("vehicle_id") and d.get("vehicle_id") != "UNASSIGNED"}
        distinct_plants = {d["plant_code"] for d in dispatches if d.get("plant_code")}
        distinct_customers = {d["customer_code"] for d in dispatches if d.get("customer_code")}

        missing_timeouts = 0
        missing_timeins = 0
        missing_vehicles = 0
        invalid_durations = 0

        for d in dispatches:
            raw_tout = d.get("time_out")
            raw_tin = d.get("time_in")
            vehicle = d.get("vehicle_id")
            t1_vol = d.get("t1_transit_mins", 0.0)

            if not raw_tout or raw_tout == "N/A":
                missing_timeouts += 1
            if not raw_tin or raw_tin == "N/A":
                missing_timeins += 1
            if not vehicle or vehicle == "UNASSIGNED":
                missing_vehicles += 1
            if t1_vol < 0:
                invalid_durations += 1

        missing_timestamps = missing_timeouts + missing_timeins

        quality_summary = DataQualitySummaryDTO(
            total_dispatches=len(dispatches),
            active_vehicle_count=len(distinct_vehicles),
            plant_count=len(distinct_plants),
            customer_count=len(distinct_customers),
            missing_timestamp_count=missing_timestamps,
            missing_vehicle_count=missing_vehicles,
        )

        blocking_conditions: List[str] = []
        warning_conditions: List[str] = []

        # 5. Evaluate Blocking & Warning Conditions
        if len(distinct_vehicles) == 0:
            blocking_conditions.append("NO_ACTIVE_VEHICLES")
        if missing_vehicles > 0 and missing_vehicles == len(dispatches):
            blocking_conditions.append("ALL_DISPATCHES_UNASSIGNED")

        # Warning / Degraded Conditions (Documented WS-06.3 Quality Rules)
        if missing_timeins > 0:
            warning_conditions.append(f"MISSING_TIME_IN_{missing_timeins}_DISPATCHES")
        if missing_timeouts > 0:
            warning_conditions.append(f"MISSING_TIME_OUT_{missing_timeouts}_DISPATCHES")
        if missing_vehicles > 0 and missing_vehicles < len(dispatches):
            warning_conditions.append(f"UNASSIGNED_VEHICLES_{missing_vehicles}_DISPATCHES")
        if invalid_durations > 0:
            warning_conditions.append(f"INVALID_DURATION_{invalid_durations}_DISPATCHES")

        # 6. Determine Final Readiness Status & Reason Code
        if blocking_conditions:
            return OptimizationReadinessDTO(
                success=True,
                status=ReadinessStatusEnum.DEGRADED,
                reason_code="BLOCKING_DATA_QUALITY_ISSUE",
                message="Dataset contains blocking operational data issues that prevent optimization.",
                quality_summary=quality_summary,
                blocking_conditions=blocking_conditions + warning_conditions,
                filters=filter_dto,
            )

        if warning_conditions:
            return OptimizationReadinessDTO(
                success=True,
                status=ReadinessStatusEnum.DEGRADED,
                reason_code="PARTIAL_DATA_QUALITY_DEGRADATION",
                message="Dataset contains minor operational data anomalies but remains suitable for optimization.",
                quality_summary=quality_summary,
                blocking_conditions=warning_conditions,
                filters=filter_dto,
            )

        # 7. Fully READY State
        return OptimizationReadinessDTO(
            success=True,
            status=ReadinessStatusEnum.READY,
            reason_code="OPTIMIZATION_READY",
            message="Operational dataset meets all readiness quality and fleet feasibility criteria.",
            quality_summary=quality_summary,
            blocking_conditions=[],
            filters=filter_dto,
        )
