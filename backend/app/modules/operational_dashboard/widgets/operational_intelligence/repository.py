from typing import Dict, Any, List, Optional
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select, func, and_, case, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, CustomerDisplayOverride
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService


@dataclass
class RawProblemCustomerObservation:
    customer_code: str
    customer_name: str
    total_trips: int
    holding_penalty_mins: float
    retention_penalty_mins: float


@dataclass
class RawDispatchIntervalObservation:
    dispatch_id: UUID
    customer_id: UUID
    customer_code: str
    vehicle_id: UUID
    time_in: Optional[datetime]
    time_out: Optional[datetime]


@dataclass
class RawSiteReadinessObservation:
    site_code: str
    site_name: str
    total_trips: int
    holding_penalty_mins: float
    compliant_transit_trips: int
    active_tms: int
    plant_fleet_denominator: int


@dataclass
class RawSiteComparisonObservation:
    site_code: str
    site_name: str
    dispatches: int
    volume_cum: float
    avg_holding_mins: float
    avg_retention_mins: float
    accurate_count: int



@dataclass
class RawHoldingRetentionObservation:
    hour_idx: int
    hour_label: str
    total_dispatches: int
    holding_penalty_mins: float
    retention_penalty_mins: float


@dataclass
class RawDASOverviewMetrics:
    total_dispatches: int
    accurate_count: int  # <= 20.0 min
    range_21_40_count: int  # 20.0 < t2a <= 40.0 min
    range_41_60_count: int  # 40.0 < t2a <= 60.0 min
    above_60_count: int  # > 60.0 min

    @property
    def moderate_count(self) -> int:
        return self.range_21_40_count

    @property
    def critical_count(self) -> int:
        return self.range_41_60_count + self.above_60_count


@dataclass
class RawDASDetailObservation:
    customer_code: str
    customer_name: str
    total_dispatches: int
    accurate_count: int
    moderate_count: int
    critical_count: int


@dataclass
class RawPotentialImpactObservation:
    total_dispatches: int
    holding_penalty_mins: float
    retention_penalty_mins: float


class OperationalIntelligenceRepository:

    """Central Data Access Repository for WS-03.2 & WS-03.3 & WS-03.4 Widgets."""

    @classmethod
    async def _apply_filters(cls, stmt: Any, filters: Dict[str, Any]) -> Any:
        plant_id = filters.get("plant_id")
        customer_id = filters.get("customer_id")
        dataset_type = filters.get("dataset_type", "REAL_ONLY")

        if plant_id and plant_id != "ALL":
            plant_subq = select(Plant.id).where(Plant.code == plant_id)
            stmt = stmt.where(Dispatch.plant_id.in_(plant_subq))

        if customer_id and customer_id != "ALL":
            cust_subq = select(Customer.id).where(Customer.code == customer_id)
            stmt = stmt.where(Dispatch.customer_id.in_(cust_subq))

        if dataset_type == "REAL_ONLY":
            stmt = stmt.where(Dispatch.is_generated == False)
        elif dataset_type == "SYNTHETIC_ONLY":
            stmt = stmt.where(Dispatch.is_generated == True)

        return stmt

    @classmethod
    async def get_problem_customer_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawProblemCustomerObservation]:
        eff_name = CustomerDisplayOverrideService.get_effective_name_expression()
        stmt = select(
            Customer.code.label("customer_code"),
            eff_name.label("effective_customer_name"),
            func.count(Dispatch.id).label("total_trips"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)), 0.0).label("holding_pen_mins"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)), 0.0).label("retention_pen_mins"),
        ).join(Customer, Dispatch.customer_id == Customer.id)\
         .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)

        stmt = await cls._apply_filters(stmt, filters)
        stmt = stmt.group_by(Customer.id, Customer.code, CustomerDisplayOverride.override_name)

        res = await session.execute(stmt)
        rows = res.all()

        return [
            RawProblemCustomerObservation(
                customer_code=r.customer_code,
                customer_name=r.effective_customer_name,
                total_trips=r.total_trips,
                holding_penalty_mins=float(r.holding_pen_mins),
                retention_penalty_mins=float(r.retention_pen_mins),
            )
            for r in rows
        ]

    @classmethod
    async def get_overlap_heatmap_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawDispatchIntervalObservation]:
        stmt = select(
            Dispatch.id.label("dispatch_id"),
            Customer.id.label("customer_id"),
            Customer.code.label("customer_code"),
            Dispatch.vehicle_id.label("vehicle_id"),
            Dispatch.time_in.label("time_in"),
            Dispatch.time_out.label("time_out"),
        ).join(Customer, Dispatch.customer_id == Customer.id)

        stmt = await cls._apply_filters(stmt, filters)
        stmt = stmt.where(and_(Dispatch.time_in.is_not(None), Dispatch.time_out.is_not(None)))

        res = await session.execute(stmt)
        rows = res.all()

        return [
            RawDispatchIntervalObservation(
                dispatch_id=r.dispatch_id,
                customer_id=r.customer_id,
                customer_code=r.customer_code,
                vehicle_id=r.vehicle_id,
                time_in=r.time_in,
                time_out=r.time_out,
            )
            for r in rows
        ]

    @classmethod
    async def get_site_fleet_denominator(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> int:
        plant_id = filters.get("plant_id")
        if not plant_id or plant_id == "ALL":
            stmt = select(func.count(Vehicle.id))
            cnt = (await session.execute(stmt)).scalar() or 0
            return cnt
        else:
            plant_subq = select(Plant.id).where(Plant.code == plant_id)
            stmt = select(func.count(func.distinct(Dispatch.vehicle_id))).where(Dispatch.plant_id.in_(plant_subq))
            cnt = (await session.execute(stmt)).scalar() or 0
            return cnt

    @classmethod
    async def get_site_readiness_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawSiteReadinessObservation]:
        fleet_denom = await cls.get_site_fleet_denominator(session, filters)
        eff_name = CustomerDisplayOverrideService.get_effective_name_expression()

        stmt = select(
            Customer.code.label("site_code"),
            eff_name.label("site_name"),
            func.count(Dispatch.id).label("total_trips"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)), 0.0).label("holding_pen_mins"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t1_transit_mins.is_not(None), Dispatch.t1_transit_mins <= 30.0), 1), else_=0)), 0
            ).label("compliant_transit_trips"),
            func.count(func.distinct(Dispatch.vehicle_id)).label("active_tms"),
        ).join(Customer, Dispatch.customer_id == Customer.id)\
         .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)

        stmt = await cls._apply_filters(stmt, filters)
        stmt = stmt.group_by(Customer.id, Customer.code, CustomerDisplayOverride.override_name)

        res = await session.execute(stmt)
        rows = res.all()

        return [
            RawSiteReadinessObservation(
                site_code=r.site_code,
                site_name=r.site_name or r.site_code,
                total_trips=r.total_trips,
                holding_penalty_mins=float(r.holding_pen_mins),
                compliant_transit_trips=r.compliant_transit_trips,
                active_tms=r.active_tms,
                plant_fleet_denominator=fleet_denom,
            )
            for r in rows
        ]

    @classmethod
    async def get_holding_retention_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawHoldingRetentionObservation]:
        hour_expr = cast(func.substr(Dispatch.time_in, 1, 2), Integer)

        stmt = select(
            hour_expr.label("hour_idx"),
            func.count(Dispatch.id).label("total_dispatches"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)), 0.0).label("holding_pen_mins"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)), 0.0).label("retention_pen_mins"),
        ).where(Dispatch.time_in.is_not(None))

        stmt = await cls._apply_filters(stmt, filters)
        stmt = stmt.group_by(hour_expr).order_by(hour_expr)

        res = await session.execute(stmt)
        rows = res.all()

        hourly_dict = {r.hour_idx: r for r in rows if r.hour_idx is not None and 0 <= r.hour_idx <= 23}

        result = []
        for h in range(24):
            hour_str = f"{h:02d}:00"
            if h in hourly_dict:
                row = hourly_dict[h]
                result.append(
                    RawHoldingRetentionObservation(
                        hour_idx=h,
                        hour_label=hour_str,
                        total_dispatches=row.total_dispatches,
                        holding_penalty_mins=float(row.holding_pen_mins),
                        retention_penalty_mins=float(row.retention_pen_mins),
                    )
                )
            else:
                result.append(
                    RawHoldingRetentionObservation(
                        hour_idx=h,
                        hour_label=hour_str,
                        total_dispatches=0,
                        holding_penalty_mins=0.0,
                        retention_penalty_mins=0.0,
                    )
                )

        return result

    @classmethod
    async def get_das_overview_metrics(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> RawDASOverviewMetrics:
        """Retrieves raw SQL aggregated counts for DAS overview with 4-tier delay classification."""
        stmt = select(
            func.count(Dispatch.id).label("total_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins <= 20.0), 1), else_=0)), 0
            ).label("acc_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins > 20.0, Dispatch.t2a_holding_mins <= 40.0), 1), else_=0)), 0
            ).label("m20_40_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins > 40.0, Dispatch.t2a_holding_mins <= 60.0), 1), else_=0)), 0
            ).label("m41_60_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins > 60.0), 1), else_=0)), 0
            ).label("gt60_cnt"),
        )

        stmt = await cls._apply_filters(stmt, filters)
        res = (await session.execute(stmt)).first()

        if not res or res.total_cnt == 0:
            return RawDASOverviewMetrics(
                total_dispatches=0,
                accurate_count=0,
                range_21_40_count=0,
                range_41_60_count=0,
                above_60_count=0,
            )

        return RawDASOverviewMetrics(
            total_dispatches=int(res.total_cnt),
            accurate_count=int(res.acc_cnt),
            range_21_40_count=int(res.m20_40_cnt),
            range_41_60_count=int(res.m41_60_cnt),
            above_60_count=int(res.gt60_cnt),
        )

    @classmethod
    async def get_das_detail_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawDASDetailObservation]:
        """Retrieves customer-level grouped SQL aggregated counts for DAS detail breakdown."""
        eff_name = CustomerDisplayOverrideService.get_effective_name_expression()
        stmt = select(
            Customer.code.label("customer_code"),
            eff_name.label("effective_customer_name"),
            func.count(Dispatch.id).label("total_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins <= 20.0), 1), else_=0)), 0
            ).label("acc_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins > 20.0, Dispatch.t2a_holding_mins <= 40.0), 1), else_=0)), 0
            ).label("mod_cnt"),
            func.coalesce(
                func.sum(case((and_(Dispatch.t2a_holding_mins.is_not(None), Dispatch.t2a_holding_mins > 40.0), 1), else_=0)), 0
            ).label("crit_cnt"),
        ).join(Customer, Dispatch.customer_id == Customer.id)\
         .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)

        stmt = await cls._apply_filters(stmt, filters)
        stmt = stmt.group_by(Customer.id, Customer.code, CustomerDisplayOverride.override_name)

        res = await session.execute(stmt)
        rows = res.all()

        return [
            RawDASDetailObservation(
                customer_code=r.customer_code,
                customer_name=r.effective_customer_name or r.customer_code,
                total_dispatches=int(r.total_cnt),
                accurate_count=int(r.acc_cnt),
                moderate_count=int(r.mod_cnt),
                critical_count=int(r.crit_cnt),
            )
            for r in rows
        ]

    @classmethod
    async def get_potential_impact_metrics(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> RawPotentialImpactObservation:
        """Aggregates holding (>20m) and retention (>10m) excess penalty minutes across active filter scope."""
        stmt = select(
            func.count(Dispatch.id).label("total_cnt"),
            func.coalesce(
                func.sum(func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)), 0.0
            ).label("holding_pen_mins"),
            func.coalesce(
                func.sum(func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)), 0.0
            ).label("retention_pen_mins"),
        )

        stmt = await cls._apply_filters(stmt, filters)
        res = (await session.execute(stmt)).first()

        if not res or res.total_cnt == 0:
            return RawPotentialImpactObservation(
                total_dispatches=0,
                holding_penalty_mins=0.0,
                retention_penalty_mins=0.0,
            )

        return RawPotentialImpactObservation(
            total_dispatches=int(res.total_cnt),
            holding_penalty_mins=float(res.holding_pen_mins),
            retention_penalty_mins=float(res.retention_pen_mins),
        )

    @classmethod
    async def get_customer_efficiency_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawProblemCustomerObservation]:
        """Retrieves raw customer-level dispatch observation metrics for WS-03.6 CEI Engine."""
        return await cls.get_problem_customer_observations(session=session, filters=filters)

    @classmethod
    async def get_site_comparison_observations(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[RawSiteComparisonObservation]:
        """Retrieves raw site-level comparison metrics across active filter scope for WS-04 Engine."""
        stmt = select(
            Plant.code.label("plant_code"),
            Plant.name.label("plant_name"),
            func.count(Dispatch.id).label("dispatches"),
            func.coalesce(func.sum(Dispatch.t1_transit_mins), 0.0).label("volume_cum"),
            func.coalesce(func.avg(Dispatch.t2a_holding_mins), 0.0).label("avg_holding_mins"),
            func.coalesce(func.avg(Dispatch.t2c_retention_mins), 0.0).label("avg_retention_mins"),
            func.coalesce(func.sum(case((Dispatch.t2a_holding_mins <= 20.0, 1), else_=0)), 0).label("accurate_count"),
        ).join(Plant, Dispatch.plant_id == Plant.id)

        stmt = await cls._apply_filters(stmt, filters)
        stmt = stmt.group_by(Plant.code, Plant.name)

        res = await session.execute(stmt)
        rows = res.all()

        return [
            RawSiteComparisonObservation(
                site_code=r.plant_code,
                site_name=r.plant_name,
                dispatches=int(r.dispatches),
                volume_cum=float(r.volume_cum),
                avg_holding_mins=float(r.avg_holding_mins),
                avg_retention_mins=float(r.avg_retention_mins),
                accurate_count=int(r.accurate_count),
            )
            for r in rows
        ]



