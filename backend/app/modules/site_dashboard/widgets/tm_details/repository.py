"""
TM Details SQL Repository
Workstream 2.6 Backend Repository
"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, CustomerDisplayOverride
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService


class TMDetailsRepository:
    """PostgreSQL Canonical SQL Queries for TM Details Subsystem."""

    @staticmethod
    async def get_filtered_dispatches(
        session: AsyncSession,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt = (
            select(
                Dispatch.id.label("dispatch_id"),
                Dispatch.dispatch_number.label("tm_no"),
                Vehicle.license_plate.label("vehicle_plate"),
                Plant.name.label("plant_name"),
                Customer.code.label("customer_code"),
                Customer.name.label("raw_customer_name"),
                CustomerDisplayOverrideService.get_effective_name_expression(),
                Dispatch.dispatch_date.label("t0_ticket_timestamp"),
                Dispatch.t2a_holding_mins,
                Dispatch.t2b_unloading_mins,
                Dispatch.t2c_retention_mins,
                Dispatch.status,
            )
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
            .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
            .join(Vehicle, Dispatch.vehicle_id == Vehicle.id, isouter=True)
        )


        plant_id = filters.get("plant_id")
        if plant_id and plant_id != "ALL":
            stmt = stmt.where(Plant.code == plant_id)

        customer_id = filters.get("customer_id")
        if customer_id and customer_id != "ALL":
            stmt = stmt.where(Customer.code == customer_id)

        # Count total matching rows
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = (await session.execute(count_stmt)).scalar() or 0

        # Pagination & Ordering
        stmt = stmt.order_by(Dispatch.dispatch_date.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await session.execute(stmt)).mappings().all()

        return [dict(r) for r in rows], total_count
