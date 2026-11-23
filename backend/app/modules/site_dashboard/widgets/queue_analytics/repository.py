"""
Queue Analytics SQL Repository
Workstream 2.5 Backend Repository
"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Plant, Customer


class QueueAnalyticsRepository:
    """PostgreSQL Canonical SQL Queries for Queue Analytics Subsystem."""

    @staticmethod
    async def get_queue_dispatch_metrics(session: AsyncSession, filters: dict[str, Any]) -> dict[str, Any]:
        stmt = (
            select(
                func.count(Dispatch.id).label("total_dispatches"),
                func.coalesce(func.sum(Dispatch.t2a_holding_mins), 0).label("sum_holding"),
                func.coalesce(func.sum(Dispatch.t2b_unloading_mins), 0).label("sum_unloading"),
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

        return {
            "total_dispatches": dispatches,
            "sum_holding": res.sum_holding if res else 0.0,
            "sum_unloading": res.sum_unloading if res else 0.0,
        }
