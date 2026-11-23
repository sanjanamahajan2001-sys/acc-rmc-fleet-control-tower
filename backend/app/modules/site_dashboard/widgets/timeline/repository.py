"""
TM Queue Timeline SQL Repository
Workstream 2.4 Backend Repository
"""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle


class TimelineRepository:
    """PostgreSQL Canonical SQL Queries for TM Queue Timeline Metrics."""

    @staticmethod
    async def get_filtered_dispatches(session: AsyncSession, filters: dict[str, Any]) -> list[dict[str, Any]]:
        stmt = (
            select(
                Dispatch.dispatch_number,
                Vehicle.license_plate.label("tm_no"),
                Dispatch.t2a_holding_mins,
                Dispatch.t2b_unloading_mins,
                Dispatch.t2c_retention_mins,
            )
            .join(Vehicle, Dispatch.vehicle_id == Vehicle.id, isouter=True)
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
            .order_by(Dispatch.dispatch_date.asc())
        )

        plant_id = filters.get("plant_id")
        if plant_id and plant_id != "ALL":
            stmt = stmt.where(Plant.code == plant_id)

        customer_id = filters.get("customer_id")
        if customer_id and customer_id != "ALL":
            stmt = stmt.where(Customer.code == customer_id)

        results = (await session.execute(stmt)).all()
        return [
            {
                "dispatch_number": r.dispatch_number,
                "tm_no": r.tm_no or "UNASSIGNED",
                "holding_mins": r.t2a_holding_mins or 0.0,
                "unloading_mins": r.t2b_unloading_mins or 0.0,
                "retention_mins": r.t2c_retention_mins or 0.0,
            }
            for r in results
        ]
