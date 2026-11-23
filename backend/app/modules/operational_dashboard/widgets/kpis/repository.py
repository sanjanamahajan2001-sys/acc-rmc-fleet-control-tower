from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle


@dataclass
class DPIObservation:
    """Row-level observation contract for Dispatch Planning Index (DPI)."""
    dispatch_id: UUID
    customer_id: Optional[UUID]
    time_out: Optional[datetime]
    t1_transit_mins: Optional[float]
    t2b_unloading_mins: Optional[float]


@dataclass
class DispatchAccuracyMetrics:
    """SQL Aggregation result for Dispatch Accuracy calculation."""
    accurate_count: int
    total_count: int


@dataclass
class SWIMetrics:
    """SQL Aggregation result for Site Waiting Index (SWI) calculation."""
    total_trips: int
    holding_penalty_sum: float
    retention_penalty_sum: float


@dataclass
class FUIMetrics:
    """SQL Aggregation result for Fleet Utilization Index (FUI) calculation."""
    active_vehicles: int
    registered_fleet_denominator: int


class KPIRepository:
    """Data Access Layer ONLY. Retrieves raw PostgreSQL observations & counts under active filters."""

    @staticmethod
    async def _apply_filters(stmt, filters: Dict[str, Any]):
        plant_id = filters.get("plant_id")
        customer_id = filters.get("customer_id")
        dataset_type = filters.get("dataset_type")

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
    async def get_dispatch_accuracy_metrics(cls, session: AsyncSession, filters: Dict[str, Any]) -> DispatchAccuracyMetrics:
        stmt_total = select(func.count(Dispatch.id))
        stmt_total = await cls._apply_filters(stmt_total, filters)
        total_cnt = (await session.execute(stmt_total)).scalar() or 0

        stmt_accurate = select(func.count(Dispatch.id)).where(Dispatch.t2a_holding_mins <= 20.0)
        stmt_accurate = await cls._apply_filters(stmt_accurate, filters)
        accurate_cnt = (await session.execute(stmt_accurate)).scalar() or 0

        return DispatchAccuracyMetrics(accurate_count=accurate_cnt, total_count=total_cnt)

    @classmethod
    async def get_swi_metrics(cls, session: AsyncSession, filters: Dict[str, Any]) -> SWIMetrics:
        stmt = select(
            func.count(Dispatch.id).label("total_trips"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2a_holding_mins - 20.0)), 0.0).label("holding_pen"),
            func.coalesce(func.sum(func.greatest(0.0, Dispatch.t2c_retention_mins - 10.0)), 0.0).label("retention_pen"),
        )
        stmt = await cls._apply_filters(stmt, filters)
        res = (await session.execute(stmt)).first()

        if not res or res.total_trips == 0:
            return SWIMetrics(total_trips=0, holding_penalty_sum=0.0, retention_penalty_sum=0.0)

        return SWIMetrics(
            total_trips=res.total_trips,
            holding_penalty_sum=float(res.holding_pen),
            retention_penalty_sum=float(res.retention_pen),
        )

    @classmethod
    async def get_dpi_observations(cls, session: AsyncSession, filters: Dict[str, Any]) -> List[DPIObservation]:
        stmt = select(
            Dispatch.id,
            Dispatch.customer_id,
            Dispatch.time_out,
            Dispatch.t1_transit_mins,
            Dispatch.t2b_unloading_mins,
        )
        stmt = await cls._apply_filters(stmt, filters)
        res = await session.execute(stmt)
        return [
            DPIObservation(
                dispatch_id=r[0],
                customer_id=r[1],
                time_out=r[2],
                t1_transit_mins=r[3],
                t2b_unloading_mins=r[4],
            )
            for r in res.all()
        ]

    @classmethod
    async def get_fui_metrics(cls, session: AsyncSession, filters: Dict[str, Any]) -> FUIMetrics:
        """
        Retrieves active vehicles count (numerator) and plant-scoped registered fleet denominator:
        - active_vehicles: COUNT(DISTINCT vehicle_id) having >= 1 dispatch under active filters.
        - registered_fleet_denominator: Total vehicles in system (if plant_id=ALL) or distinct vehicles assigned to plant.
        """
        # Numerator: Active vehicles under active filters
        stmt_act = select(func.count(func.distinct(Dispatch.vehicle_id)))
        stmt_act = await cls._apply_filters(stmt_act, filters)
        active_veh = (await session.execute(stmt_act)).scalar() or 0

        # Denominator: Registered fleet assigned to plant scope (or total registered vehicles if ALL)
        plant_id = filters.get("plant_id")
        if not plant_id or plant_id == "ALL":
            stmt_den = select(func.count(Vehicle.id))
            reg_fleet = (await session.execute(stmt_den)).scalar() or 0
        else:
            plant_subq = select(Plant.id).where(Plant.code == plant_id)
            stmt_den = select(func.count(func.distinct(Dispatch.vehicle_id))).where(Dispatch.plant_id.in_(plant_subq))
            reg_fleet = (await session.execute(stmt_den)).scalar() or 0

        return FUIMetrics(active_vehicles=active_veh, registered_fleet_denominator=reg_fleet)

    @classmethod
    async def get_total_dispatch_count(cls, session: AsyncSession, filters: Dict[str, Any]) -> int:
        stmt = select(func.count(Dispatch.id))
        stmt = await cls._apply_filters(stmt, filters)
        return (await session.execute(stmt)).scalar() or 0
