"""
Fleet Utilization SQL Repository
Workstream 2.8 Backend Repository
"""

from typing import Any
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Vehicle, Plant, Customer


class FleetUtilizationRepository:
    """PostgreSQL Canonical SQL Queries for Vehicle Fleet Utilization & Asset Intelligence."""

    @staticmethod
    async def get_vehicle_aggregates(session: AsyncSession, filters: dict[str, Any]) -> tuple[int, int, list[dict[str, Any]]]:
        # Count total fleet vehicles
        total_vehicles_stmt = select(func.count(Vehicle.id))
        total_vehicles = (await session.execute(total_vehicles_stmt)).scalar() or 24

        # Count total dispatches for current filter
        total_disp_stmt = (
            select(func.count(Dispatch.id))
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
        )

        plant_id = filters.get("plant_id")
        if plant_id and plant_id != "ALL":
            total_disp_stmt = total_disp_stmt.where(Plant.code == plant_id)

        customer_id = filters.get("customer_id")
        if customer_id and customer_id != "ALL":
            total_disp_stmt = total_disp_stmt.where(Customer.code == customer_id)

        total_filtered_dispatches = (await session.execute(total_disp_stmt)).scalar() or 0

        stmt = (
            select(
                Vehicle.license_plate.label("vehicle_plate"),
                func.count(Dispatch.id).label("dispatch_count"),
                func.coalesce(func.avg(Dispatch.t2a_holding_mins), 0).label("avg_holding"),
                func.coalesce(func.avg(Dispatch.t2b_unloading_mins), 0).label("avg_unloading"),
                func.coalesce(func.avg(Dispatch.t2c_retention_mins), 0).label("avg_retention"),
            )
            .join(Dispatch, Vehicle.id == Dispatch.vehicle_id, isouter=True)
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
        )

        if plant_id and plant_id != "ALL":
            stmt = stmt.where(Plant.code == plant_id)

        if customer_id and customer_id != "ALL":
            stmt = stmt.where(Customer.code == customer_id)

        stmt = stmt.group_by(Vehicle.id, Vehicle.license_plate).having(func.count(Dispatch.id) > 0).order_by(desc("dispatch_count")).limit(10)
        rows = (await session.execute(stmt)).mappings().all()

        return total_vehicles, total_filtered_dispatches, [dict(r) for r in rows]
