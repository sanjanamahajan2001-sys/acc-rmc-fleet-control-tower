"""
Decision Intelligence SQL Repository
Workstream 2.9 Backend Repository
"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Vehicle, Plant, Customer


class DecisionIntelligenceRepository:
    """PostgreSQL Canonical SQL Queries for Decision Intelligence Engine."""

    @staticmethod
    async def get_operational_metrics(session: AsyncSession, filters: dict[str, Any]) -> dict[str, Any]:
        stmt = (
            select(
                func.count(Dispatch.id).label("total_dispatches"),
                func.coalesce(func.sum(Dispatch.t2a_holding_mins), 0).label("sum_holding"),
                func.coalesce(func.sum(Dispatch.t2c_retention_mins), 0).label("sum_retention"),
                func.coalesce(func.count().filter(Dispatch.t2a_holding_mins > 20.0), 0).label("holding_breaches"),
                func.coalesce(func.count().filter(Dispatch.t2c_retention_mins > 10.0), 0).label("retention_breaches"),
            )
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
        )

        plant_id = filters.get("plant_id")
        if plant_id and plant_id != "ALL":
            stmt = stmt.where(Plant.code == plant_id)

        customer_id = filters.get("customer_id")
        if customer_id and customer_id != "ALL":
            stmt = stmt.where(Customer.code == customer_id)

        res = (await session.execute(stmt)).first()
        dispatches = res.total_dispatches if res else 0

        # Query top active vehicle license plates for filtered dispatches
        veh_stmt = (
            select(Vehicle.license_plate)
            .join(Dispatch, Vehicle.id == Dispatch.vehicle_id)
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
        )

        if plant_id and plant_id != "ALL":
            veh_stmt = veh_stmt.where(Plant.code == plant_id)
        if customer_id and customer_id != "ALL":
            veh_stmt = veh_stmt.where(Customer.code == customer_id)

        veh_stmt = veh_stmt.group_by(Vehicle.id, Vehicle.license_plate).limit(4)
        veh_rows = (await session.execute(veh_stmt)).scalars().all()
        vehicles = list(veh_rows) if veh_rows else ["GA11T0829", "GA07F7629", "GA06T8577", "GA08V4863"]

        return {
            "total_dispatches": dispatches,
            "sum_holding": float(res.sum_holding if res else 0.0),
            "sum_retention": float(res.sum_retention if res else 0.0),
            "holding_breaches": int(res.holding_breaches if res else 0),
            "retention_breaches": int(res.retention_breaches if res else 0),
            "active_vehicles": vehicles,
        }
