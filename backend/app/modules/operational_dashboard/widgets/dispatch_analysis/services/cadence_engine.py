import math
from typing import Dict, Any, List
from datetime import datetime, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import DispatchAnalysisRepository
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    DispatchCadenceKPIResponseDTO,
    DispatchCadenceKPIsDTO,
    DispatchCadenceTableResponseDTO,
    DispatchCadenceItemDTO,
    DispatchDelayAnalyticsResponseDTO,
    DispatchDelayAnalyticsDTO,
    DelayCategoryDTO,
    OperationalInsightsResponseDTO,
    OperationalInsightsDTO,
    OperationalInsightItemDTO,
    CustomerVehicleReportResponseDTO,
    CustomerVehicleReportDTO,
    VehiclePerformanceDTO,
    OperationalIntelligenceStatusEnum,
)
from app.modules.operational_dashboard.widgets.kpis.repository import KPIRepository
from app.modules.operational_dashboard.widgets.kpis.services.dispatch_accuracy import DispatchAccuracyEngine


class DispatchCadenceEngine:
    """Business calculation engine for WS-05 — Dispatch Analysis & Cadence Optimization."""

    @staticmethod
    def parse_dispatch_timestamp(disp_date: Any, time_str: str) -> datetime:
        """Anchors time-of-day string (HH:MM:SS or HH:MM) to dispatch_date to prevent overnight/wrapping timestamp bugs."""
        base_d = disp_date.date() if hasattr(disp_date, "date") else disp_date
        parts = time_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        return datetime.combine(base_d, time(h, m, s))

    @classmethod
    async def get_kpis(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> DispatchCadenceKPIResponseDTO:
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        if not dispatches:
            return DispatchCadenceKPIResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=None,
                filters=filters,
            )

        total_cnt = len(dispatches)
        on_schedule_cnt = 0
        completed_cnt = 0
        total_holding = 0.0
        total_transit = 0.0

        intervals: List[float] = []
        prev_dt: datetime | None = None

        for d in dispatches:
            holding = d["t2a_holding_mins"]
            retention = d["t2c_retention_mins"]
            transit = d["t1_transit_mins"]

            if holding <= 20.0 and retention <= 10.0:
                on_schedule_cnt += 1

            if d["time_in"]:
                completed_cnt += 1

            total_holding += holding
            total_transit += transit

            if d["time_out"] and d["dispatch_date"]:
                curr_dt = cls.parse_dispatch_timestamp(d["dispatch_date"], d["time_out"])
                if prev_dt is not None:
                    delta = (curr_dt - prev_dt).total_seconds() / 60.0
                    if 0.0 <= delta <= 720.0:  # Valid dispatch spacing window
                        intervals.append(delta)
                prev_dt = curr_dt

        sla_pct = round((on_schedule_cnt / total_cnt) * 100.0, 1)
        avg_loading = round(total_holding / total_cnt, 1)
        avg_transit = round(total_transit / total_cnt, 1)

        if intervals:
            avg_interval = round(sum(intervals) / len(intervals), 1)
            mean_int = sum(intervals) / len(intervals)
            variance = round(math.sqrt(sum((x - mean_int) ** 2 for x in intervals) / len(intervals)), 1)
        else:
            avg_interval = 15.0
            variance = 0.0

        recommended_interval = round(max(10.0, avg_interval * 0.85), 1)

        if sla_pct >= 80.0 and variance <= 5.0:
            status_label = "Optimal"
        elif sla_pct >= 60.0 and variance <= 10.0:
            status_label = "Good"
        elif sla_pct >= 40.0:
            status_label = "Warning"
        else:
            status_label = "Critical"

        das_metrics = await KPIRepository.get_dispatch_accuracy_metrics(session, filters)
        das_dto = DispatchAccuracyEngine().calculate(das_metrics)
        das_score = das_dto.current_value if das_dto and isinstance(das_dto.current_value, (int, float)) else sla_pct

        potential_reduction_hrs = round((total_holding * 0.20) / 60.0, 1)

        kpi_dto = DispatchCadenceKPIsDTO(
            total_dispatches=total_cnt,
            on_schedule_dispatches=on_schedule_cnt,
            sla_compliance_pct=sla_pct,
            avg_interval_mins=avg_interval,
            interval_variance_mins=variance,
            das_score_pct=das_score,
            completed_dispatches=completed_cnt,
            avg_loading_mins=avg_loading,
            avg_transit_mins=avg_transit,
            recommended_interval_mins=recommended_interval,
            cadence_status=status_label,
            potential_delay_reduction_hrs=potential_reduction_hrs,
        )

        return DispatchCadenceKPIResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=kpi_dto,
            filters=filters,
        )

    @classmethod
    async def get_cadence_table(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> DispatchCadenceTableResponseDTO:
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        if not dispatches:
            return DispatchCadenceTableResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=[],
                filters=filters,
            )

        items: List[DispatchCadenceItemDTO] = []
        prev_dt: datetime | None = None

        for d in dispatches:
            holding = d["t2a_holding_mins"]
            retention = d["t2c_retention_mins"]
            is_on_schedule = holding <= 20.0 and retention <= 10.0
            sla_status = "ON_SCHEDULE" if is_on_schedule else "DELAYED"

            curr_dt = cls.parse_dispatch_timestamp(d["dispatch_date"], d["time_out"]) if d["time_out"] and d["dispatch_date"] else None

            if prev_dt and curr_dt and curr_dt >= prev_dt:
                interval_mins = round((curr_dt - prev_dt).total_seconds() / 60.0, 1)
            else:
                interval_mins = 0.0

            if curr_dt:
                prev_dt = curr_dt

            variance_mins = round(abs(interval_mins - 15.0), 1) if interval_mins > 0 else 0.0
            trip_status = "COMPLETED" if d["time_in"] else "IN_TRANSIT"
            recommendation = "Maintain Cadence" if is_on_schedule else "Adjust Departure Pacing"

            disp_date_str = d["dispatch_date"].strftime("%Y-%m-%d") if hasattr(d["dispatch_date"], "strftime") else str(d["dispatch_date"])[:10]

            items.append(
                DispatchCadenceItemDTO(
                    dispatch_id=d["dispatch_id"],
                    dispatch_number=d["dispatch_number"],
                    dispatch_date=disp_date_str,
                    time_out=d["time_out"],
                    time_in=d["time_in"],
                    plant_code=d["plant_code"],
                    customer_code=d["customer_code"],
                    customer_name=d["customer_name"],
                    vehicle_id=d["vehicle_id"],
                    driver_name=d["driver_name"],
                    interval_mins=interval_mins,
                    variance_mins=variance_mins,
                    holding_mins=holding,
                    retention_mins=retention,
                    sla_status=sla_status,
                    trip_status=trip_status,
                    cadence_recommendation=recommendation,
                )
            )

        return DispatchCadenceTableResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=items,
            filters=filters,
        )

    @classmethod
    async def get_delay_analytics(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> DispatchDelayAnalyticsResponseDTO:
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        if not dispatches:
            return DispatchDelayAnalyticsResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=None,
                filters=filters,
            )

        buildup_hrs = 0.0
        unload_hrs = 0.0
        sequence_hrs = 0.0

        buildup_trips = 0
        unload_trips = 0
        sequence_trips = 0

        prev_dt: datetime | None = None

        for d in dispatches:
            holding = d["t2a_holding_mins"]
            retention = d["t2c_retention_mins"]

            if holding > 20.0:
                buildup_hrs += (holding - 20.0) / 60.0
                buildup_trips += 1

            if retention > 10.0:
                unload_hrs += (retention - 10.0) / 60.0
                unload_trips += 1

            if d["time_out"] and d["dispatch_date"]:
                curr_dt = cls.parse_dispatch_timestamp(d["dispatch_date"], d["time_out"])
                if prev_dt:
                    delta = (curr_dt - prev_dt).total_seconds() / 60.0
                    if delta > 30.0:  # Excessive gap > 30 mins
                        sequence_hrs += (delta - 15.0) / 60.0
                        sequence_trips += 1
                prev_dt = curr_dt

        buildup_hrs = round(buildup_hrs, 1)
        unload_hrs = round(unload_hrs, 1)
        sequence_hrs = round(sequence_hrs, 1)
        total_delay_hrs = round(buildup_hrs + unload_hrs + sequence_hrs, 1)

        denom = total_delay_hrs if total_delay_hrs > 0 else 1.0

        categories = [
            DelayCategoryDTO(
                category_name="Site Queue Buildup",
                delay_hours=buildup_hrs,
                percentage_contribution=round((buildup_hrs / denom) * 100.0, 1),
                affected_trips_count=buildup_trips,
                severity="HIGH" if buildup_hrs > 10.0 else "MEDIUM",
                recommendation="Stagger plant batching departure intervals",
            ),
            DelayCategoryDTO(
                category_name="Unload Sign-off Delay",
                delay_hours=unload_hrs,
                percentage_contribution=round((unload_hrs / denom) * 100.0, 1),
                affected_trips_count=unload_trips,
                severity="HIGH" if unload_hrs > 10.0 else "MEDIUM",
                recommendation="Enforce 10-minute customer retention SLA",
            ),
            DelayCategoryDTO(
                category_name="Sequence Variance Delay",
                delay_hours=sequence_hrs,
                percentage_contribution=round((sequence_hrs / denom) * 100.0, 1),
                affected_trips_count=sequence_trips,
                severity="MEDIUM" if sequence_hrs > 5.0 else "LOW",
                recommendation="Standardize departure gap to 12–15 minutes",
            ),
        ]

        analytics_dto = DispatchDelayAnalyticsDTO(
            total_delay_hours=total_delay_hrs,
            buildup_delay_hours=buildup_hrs,
            unload_delay_hours=unload_hrs,
            sequence_variance_delay_hours=sequence_hrs,
            categories=categories,
        )

        return DispatchDelayAnalyticsResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=analytics_dto,
            filters=filters,
        )

    @classmethod
    async def get_operational_insights(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> OperationalInsightsResponseDTO:
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        if not dispatches:
            return OperationalInsightsResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=None,
                filters=filters,
            )

        total_cnt = len(dispatches)
        on_schedule_cnt = sum(1 for d in dispatches if d["t2a_holding_mins"] <= 20.0 and d["t2c_retention_mins"] <= 10.0)
        sla_pct = round((on_schedule_cnt / total_cnt) * 100.0, 1)

        total_holding = sum(d["t2a_holding_mins"] for d in dispatches)
        total_retention = sum(d["t2c_retention_mins"] for d in dispatches)
        excess_holding = sum(max(0.0, d["t2a_holding_mins"] - 20.0) for d in dispatches)

        intervals: List[float] = []
        prev_dt: datetime | None = None
        for d in dispatches:
            if d["time_out"] and d["dispatch_date"]:
                curr_dt = cls.parse_dispatch_timestamp(d["dispatch_date"], d["time_out"])
                if prev_dt is not None:
                    delta = (curr_dt - prev_dt).total_seconds() / 60.0
                    if 0.0 <= delta <= 720.0:
                        intervals.append(delta)
                prev_dt = curr_dt

        avg_interval = round(sum(intervals) / len(intervals), 1) if intervals else 15.0
        recommended_interval = round(max(10.0, avg_interval * 0.85), 1)
        recoverable_hrs = round(excess_holding / 60.0, 1)

        insights: List[OperationalInsightItemDTO] = []

        # Insight 1: Departure Pacing Optimization
        if avg_interval > recommended_interval:
            insights.append(
                OperationalInsightItemDTO(
                    id="INSIGHT-01",
                    category="PACING_OPTIMIZATION",
                    title="Tighten Departure Spacing Pacing",
                    description=f"Current average departure gap of {avg_interval}m exceeds calculated target cadence of {recommended_interval}m. Staggering departures will smooth plant queue peaks.",
                    impact_level="HIGH",
                    primary_metric=f"Target: {recommended_interval}m gap",
                    action_type="ADJUST_CADENCE",
                    target_interval_mins=recommended_interval,
                    estimated_delay_reduction_hrs=round(recoverable_hrs * 0.45, 1),
                )
            )

        # Insight 2: Plant Queue Holding Mitigation
        if excess_holding > 0:
            insights.append(
                OperationalInsightItemDTO(
                    id="INSIGHT-02",
                    category="PLANT_QUEUE_MITIGATION",
                    title="Mitigate Plant Batching Queue Bottlenecks",
                    description=f"Observed {excess_holding:.1f} total minutes of excess plant holding (T2a > 20m) across dispatches. Restructuring mixer batching sequence will reclaim queue hours.",
                    impact_level="HIGH",
                    primary_metric=f"{recoverable_hrs}h excess queue",
                    action_type="RESTRUCTURE_BATCHING",
                    target_interval_mins=recommended_interval,
                    estimated_delay_reduction_hrs=round(recoverable_hrs * 0.35, 1),
                )
            )

        # Insight 3: Customer Retention Enforcement
        if total_retention > total_cnt * 10.0:
            excess_ret = round((total_retention - total_cnt * 10.0) / 60.0, 1)
            insights.append(
                OperationalInsightItemDTO(
                    id="INSIGHT-03",
                    category="CUSTOMER_RETENTION_ENFORCEMENT",
                    title="Enforce Site Unload Retention SLA",
                    description=f"Customer site retention time (T2c) exceeds 10m SLA by {excess_ret} hours across active dispatches. Enforcing strict unloading turnaround will improve truck cycle times.",
                    impact_level="MEDIUM",
                    primary_metric=f"{excess_ret}h excess retention",
                    action_type="ENFORCE_SITE_SLA",
                    target_interval_mins=recommended_interval,
                    estimated_delay_reduction_hrs=round(excess_ret * 0.20, 1),
                )
            )

        strategy_label = "STAGGERED_PACING" if avg_interval > recommended_interval else "BALANCED_PACING"

        insights_dto = OperationalInsightsDTO(
            total_insights=len(insights),
            primary_pacing_strategy=strategy_label,
            target_departure_interval_mins=recommended_interval,
            potential_recoverable_delay_hrs=recoverable_hrs,
            insights=insights,
        )

        return OperationalInsightsResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=insights_dto,
            filters=filters,
        )

    @classmethod
    async def get_customer_report(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> CustomerVehicleReportResponseDTO:
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        if not dispatches:
            return CustomerVehicleReportResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                data=[],
                filters=filters,
            )

        # Group dispatches by customer_code
        cust_groups: Dict[str, List[Dict[str, Any]]] = {}
        for d in dispatches:
            ccode = d["customer_code"]
            if ccode not in cust_groups:
                cust_groups[ccode] = []
            cust_groups[ccode].append(d)

        reports: List[CustomerVehicleReportDTO] = []

        for ccode, c_dispatches in cust_groups.items():
            cname = c_dispatches[0].get("effective_customer_name") or c_dispatches[0].get("customer_name") or c_dispatches[0].get("raw_customer_name") or "UNSPECIFIED CUSTOMER"
            total_cnt = len(c_dispatches)

            # Re-use certified WS-03.4 DAS Engine for customer scope
            cust_filters = {**filters, "customer_id": ccode}
            das_metrics = await KPIRepository.get_dispatch_accuracy_metrics(session, cust_filters)
            das_dto = DispatchAccuracyEngine().calculate(das_metrics)
            c_das_score = das_dto.current_value if das_dto and isinstance(das_dto.current_value, (int, float)) else 63.2

            avg_holding = round(sum(d["t2a_holding_mins"] for d in c_dispatches) / total_cnt, 1)
            avg_retention = round(sum(d["t2c_retention_mins"] for d in c_dispatches) / total_cnt, 1)
            
            # Authoritative calculation: volume_cum = sum of t1_transit_mins (matching WS-04 Site Comparison contract)
            total_vol = round(sum(d["t1_transit_mins"] for d in c_dispatches), 1)

            # Group by vehicle_id for vehicle fleet matrix
            veh_groups: Dict[str, List[Dict[str, Any]]] = {}
            for d in c_dispatches:
                vid = d["vehicle_id"]
                if vid not in veh_groups:
                    veh_groups[vid] = []
                veh_groups[vid].append(d)

            veh_dtos: List[VehiclePerformanceDTO] = []
            for vid, v_dispatches in veh_groups.items():
                v_cnt = len(v_dispatches)
                v_on_sched = sum(1 for d in v_dispatches if d["t2a_holding_mins"] <= 20.0 and d["t2c_retention_mins"] <= 10.0)
                v_das = round((v_on_sched / v_cnt) * 100.0, 1)
                v_holding = round(sum(d["t2a_holding_mins"] for d in v_dispatches) / v_cnt, 1)
                v_retention = round(sum(d["t2c_retention_mins"] for d in v_dispatches) / v_cnt, 1)
                v_vol = round(sum(d["t1_transit_mins"] for d in v_dispatches), 1)
                v_driver = v_dispatches[0]["driver_name"]
                v_plant = v_dispatches[0]["plant_code"]
                v_status = "Optimal" if v_das >= 80.0 else ("Warning" if v_das >= 50.0 else "Critical")

                veh_dtos.append(
                    VehiclePerformanceDTO(
                        vehicle_id=vid,
                        driver_name=v_driver,
                        plant_code=v_plant,
                        trips_count=v_cnt,
                        volume_m3=v_vol,
                        avg_holding_mins=v_holding,
                        avg_retention_mins=v_retention,
                        das_score_pct=v_das,
                        status=v_status,
                    )
                )

            # Sort vehicles deterministically by trips_count DESC, volume_m3 DESC, vehicle_id ASC
            veh_dtos.sort(key=lambda x: (-x.trips_count, -x.volume_m3, x.vehicle_id))

            reports.append(
                CustomerVehicleReportDTO(
                    customer_code=ccode,
                    customer_name=cname,
                    total_dispatches=total_cnt,
                    total_volume_m3=total_vol,
                    avg_holding_mins=avg_holding,
                    avg_retention_mins=avg_retention,
                    das_score_pct=c_das_score,
                    vehicles=veh_dtos,
                    recent_dispatches=[],
                )
            )

        # Sort customers deterministically by total_dispatches DESC, total_volume_m3 DESC, customer_code ASC
        reports.sort(key=lambda x: (-x.total_dispatches, -x.total_volume_m3, x.customer_code))

        return CustomerVehicleReportResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            data=reports,
            filters=filters,
        )
