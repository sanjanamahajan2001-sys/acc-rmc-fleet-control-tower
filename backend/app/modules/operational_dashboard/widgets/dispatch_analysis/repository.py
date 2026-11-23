from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, Driver, CustomerDisplayOverride
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService


class DispatchAnalysisRepository:
    """Repository for querying production database dispatches and customer-vehicle-driver-trip lineage."""

    @classmethod
    async def get_scoped_dispatches(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        plant_id = filters.get("plant_id", "ALL")
        customer_id = filters.get("customer_id", "ALL")
        dataset_type = filters.get("dataset_type", "REAL_ONLY")

        eff_customer_name = CustomerDisplayOverrideService.get_effective_name_expression()
        stmt = select(
            Dispatch.id.label("dispatch_id"),
            Dispatch.dispatch_number,
            Dispatch.dispatch_date,
            Dispatch.time_out,
            Dispatch.time_in,
            Dispatch.t1_transit_mins,
            Dispatch.t2a_holding_mins,
            Dispatch.t2c_retention_mins,
            Dispatch.is_generated,
            Plant.code.label("plant_code"),
            Plant.name.label("plant_name"),
            Customer.code.label("customer_code"),
            Customer.name.label("raw_customer_name"),
            eff_customer_name.label("effective_customer_name"),
            Vehicle.code.label("vehicle_id"),
            Driver.name.label("driver_name"),
        ).join(
            Plant, Dispatch.plant_id == Plant.id, isouter=True
        ).join(
            Customer, Dispatch.customer_id == Customer.id, isouter=True
        ).outerjoin(
            CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id
        ).join(
            Vehicle, Dispatch.vehicle_id == Vehicle.id, isouter=True
        ).join(
            Driver, Dispatch.driver_id == Driver.id, isouter=True
        )

        if plant_id and plant_id not in ("ALL", None):
            stmt = stmt.where(Plant.code == plant_id)
        if customer_id and customer_id not in ("ALL", None):
            stmt = stmt.where(Customer.code == customer_id)

        if dataset_type == "REAL_ONLY":
            stmt = stmt.where(Dispatch.is_generated == False)
        elif dataset_type == "SYNTHETIC_ONLY":
            stmt = stmt.where(Dispatch.is_generated == True)

        stmt = stmt.order_by(Dispatch.dispatch_date.asc(), Dispatch.time_out.asc())

        res = await session.execute(stmt)
        rows = res.all()

        return [
            {
                "dispatch_id": str(r.dispatch_id),
                "dispatch_number": r.dispatch_number or "N/A",
                "dispatch_date": r.dispatch_date,
                "time_out": r.time_out,
                "time_in": r.time_in,
                "t1_transit_mins": float(r.t1_transit_mins or 0.0),
                "t2a_holding_mins": float(r.t2a_holding_mins or 0.0),
                "t2c_retention_mins": float(r.t2c_retention_mins or 0.0),
                "is_generated": r.is_generated,
                "plant_code": r.plant_code or "ALL",
                "plant_name": r.plant_name or "Unknown Plant",
                "customer_code": r.customer_code or "UNSPECIFIED_CUSTOMER",
                "raw_customer_name": r.raw_customer_name or "UNSPECIFIED CUSTOMER",
                "customer_name": r.effective_customer_name or r.raw_customer_name or "UNSPECIFIED CUSTOMER",
                "effective_customer_name": r.effective_customer_name or r.raw_customer_name or "UNSPECIFIED CUSTOMER",
                "vehicle_id": r.vehicle_id or "UNASSIGNED",
                "driver_name": r.driver_name or "Unassigned Driver",
            }
            for r in rows
        ]


class HistoricalRouteRepository:
    """
    Dedicated database repository for querying and cleansing authoritative historical ERP/VTS dispatch
    and trip data for WS-ROUT-1 Route Analysis Decision Support Engine.
    """

    @classmethod
    async def get_raw_candidate_dispatches(
        cls,
        session: AsyncSession,
        site_id: Any,
        plant_ids: List[Any],
        window_start: datetime,
        window_end: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Queries completed dispatches for the requested plant IDs and site within the rolling window.
        Enforces Stage 1-3 cleansing filters directly in PostgreSQL:
        - status == 'COMPLETED'
        - plant_id in candidate plant_ids
        - dispatch_date between window_start and window_end
        - non-null plant_id, ticket_id, vehicle_id
        """
        from app.modules.erp.models import Site, Ticket, Order

        stmt = (
            select(
                Dispatch.id.label("dispatch_id"),
                Dispatch.dispatch_number,
                Dispatch.plant_id,
                Dispatch.customer_id,
                Dispatch.dispatch_date,
                Dispatch.time_out,
                Dispatch.time_in,
                Dispatch.date_in,
                Dispatch.t1_transit_mins,
                Dispatch.distance_km,
                Dispatch.status,
                Dispatch.is_generated,
                Dispatch.source_lineage,
                Plant.code.label("plant_code"),
                Plant.name.label("plant_name"),
                Site.id.label("site_id"),
                Site.code.label("site_code"),
                Site.name.label("site_name"),
            )
            .join(Plant, Dispatch.plant_id == Plant.id)
            .join(Ticket, Dispatch.ticket_id == Ticket.id)
            .join(Order, Ticket.order_id == Order.id)
            .join(Site, Site.id == site_id)
            .where(
                Dispatch.status == "COMPLETED",
                Dispatch.plant_id.in_(plant_ids),
                Dispatch.dispatch_date >= window_start,
                Dispatch.dispatch_date <= window_end,
                Dispatch.is_deleted == False,
            )
            .order_by(Dispatch.dispatch_date.desc(), Dispatch.created_at.desc())
        )

        res = await session.execute(stmt)
        rows = res.all()

        return [
            {
                "dispatch_id": r.dispatch_id,
                "dispatch_number": r.dispatch_number,
                "plant_id": r.plant_id,
                "customer_id": r.customer_id,
                "dispatch_date": r.dispatch_date,
                "time_out": r.time_out,
                "time_in": r.time_in,
                "date_in": r.date_in,
                "t1_transit_mins": r.t1_transit_mins,
                "distance_km": r.distance_km,
                "status": r.status,
                "is_generated": r.is_generated,
                "source_lineage": r.source_lineage,
                "plant_code": r.plant_code,
                "plant_name": r.plant_name,
                "site_id": r.site_id,
                "site_code": r.site_code,
                "site_name": r.site_name,
            }
            for r in rows
        ]

