"""
Site Performance SQL Repository
Workstream 2.7 Backend Repository
"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Plant, Customer


class SitePerformanceRepository:
    """PostgreSQL Canonical SQL Queries for Site Performance & SLA Subsystem."""

    @staticmethod
    async def get_performance_aggregates(session: AsyncSession, filters: dict[str, Any]) -> dict[str, Any]:
        stmt = (
            select(
                func.count(Dispatch.id).label("total_dispatches"),
                func.coalesce(func.sum(Dispatch.t2a_holding_mins), 0).label("sum_holding"),
                func.coalesce(func.max(Dispatch.t2a_holding_mins), 0).label("max_holding"),
                func.coalesce(func.sum(Dispatch.t2b_unloading_mins), 0).label("sum_unloading"),
                func.coalesce(func.sum(Dispatch.t2c_retention_mins), 0).label("sum_retention"),
                func.coalesce(func.max(Dispatch.t2c_retention_mins), 0).label("max_retention"),
                func.coalesce(func.count().filter(Dispatch.t2a_holding_mins > 20.0), 0).label("holding_breaches"),
                func.coalesce(func.count().filter(Dispatch.t2c_retention_mins > 10.0), 0).label("retention_breaches"),
                func.coalesce(func.count().filter(Dispatch.t2a_holding_mins <= 10.0), 0).label("low_delays"),
                func.coalesce(func.count().filter((Dispatch.t2a_holding_mins > 10.0) & (Dispatch.t2a_holding_mins <= 20.0)), 0).label("medium_delays"),
                func.coalesce(func.count().filter((Dispatch.t2a_holding_mins > 20.0) & (Dispatch.t2a_holding_mins <= 40.0)), 0).label("high_delays"),
                func.coalesce(func.count().filter(Dispatch.t2a_holding_mins > 40.0), 0).label("critical_delays"),
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
            "sum_holding": float(res.sum_holding if res else 0.0),
            "max_holding": float(res.max_holding if res else 0.0),
            "sum_unloading": float(res.sum_unloading if res else 0.0),
            "sum_retention": float(res.sum_retention if res else 0.0),
            "max_retention": float(res.max_retention if res else 0.0),
            "holding_breaches": int(res.holding_breaches if res else 0),
            "retention_breaches": int(res.retention_breaches if res else 0),
            "low_delays": int(res.low_delays if res else 0),
            "medium_delays": int(res.medium_delays if res else 0),
            "high_delays": int(res.high_delays if res else 0),
            "critical_delays": int(res.critical_delays if res else 0),
        }
