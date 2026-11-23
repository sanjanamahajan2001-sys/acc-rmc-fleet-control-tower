"""
PersistenceCoordinator Subsystem for Atomic Database Transactions
Converts PersistableBatch canonical DTOs into SQLAlchemy entities and commits them
within a single Phase 0 UnitOfWork / AsyncSession boundary.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import (
    Customer,
    Dispatch,
    Driver,
    Invoice,
    Order,
    Plant,
    Site,
    Ticket,
    Trip,
    Vehicle,
)
from app.modules.erp.validation.schemas import PersistableBatch


class PersistenceCoordinator:
    """
    Coordinates transaction-safe atomic persistence of validated PersistableBatch payloads.
    Guarantees all-or-nothing execution with zero partial commits.
    """

    @staticmethod
    async def persist_batch(
        session: AsyncSession, batch: PersistableBatch
    ) -> dict[str, int]:
        """
        Persist plants, sites, customers, vehicles, drivers, orders, tickets, dispatches, invoices, and trips
        in strict dependency order within an active AsyncSession transaction.
        """
        counts = {
            "plants": 0,
            "sites": 0,
            "customers": 0,
            "vehicles": 0,
            "drivers": 0,
            "orders": 0,
            "tickets": 0,
            "dispatches": 0,
            "dispatches_inserted": 0,
            "dispatches_updated": 0,
            "invoices": 0,
            "trips": 0,
            "trips_inserted": 0,
            "trips_updated": 0,
        }

        from sqlalchemy import select

        # 1. Plants
        for p in batch.plants:
            res = await session.execute(select(Plant).where(Plant.code == p.code))
            existing = res.scalars().first()
            if existing:
                p.id = existing.id
                if p.latitude is not None and (existing.latitude is None or existing.longitude is None):
                    existing.latitude = p.latitude
                    existing.longitude = p.longitude
            else:
                plant_entity = Plant(
                    id=p.id, code=p.code, name=p.name, location=p.location,
                    plant_type=p.plant_type, latitude=p.latitude, longitude=p.longitude,
                    is_generated=p.is_generated, generation_reason=p.generation_reason, source_lineage=p.source_lineage
                )
                session.add(plant_entity)
            for disp in batch.dispatches:
                if disp.plant_code == p.code:
                    disp.plant_id = p.id
            for s in batch.sites:
                if s.plant_code == p.code:
                    s.plant_id = p.id
            counts["plants"] += 1

        # 2. Sites
        for s in batch.sites:
            res = await session.execute(select(Site).where(Site.code == s.code))
            existing = res.scalars().first()
            if existing:
                s.id = existing.id
                if s.latitude is not None and (existing.latitude is None or existing.longitude is None):
                    existing.latitude = s.latitude
                    existing.longitude = s.longitude
            else:
                site_entity = Site(
                    id=s.id, code=s.code, name=s.name, plant_id=s.plant_id,
                    original_address=s.original_address, latitude=s.latitude, longitude=s.longitude,
                    geofence_radius_meters=s.geofence_radius_meters,
                    is_generated=s.is_generated, generation_reason=s.generation_reason, source_lineage=s.source_lineage
                )
                session.add(site_entity)
            counts["sites"] += 1
            # If the site represents a plant location and has coordinates, propagate coordinates to the parent Plant
            if s.latitude is not None and s.plant_id:
                s_name_lower = s.name.lower() if s.name else ""
                if "plant" in s_name_lower:
                    p_res = await session.execute(select(Plant).where(Plant.id == s.plant_id))
                    p_curr = p_res.scalars().first()
                    if p_curr and (p_curr.latitude is None or p_curr.longitude is None):
                        p_curr.latitude = s.latitude
                        p_curr.longitude = s.longitude

        # 3. Customers
        for c in batch.customers:
            res = await session.execute(select(Customer).where(Customer.code == c.code))
            existing = res.scalars().first()
            if existing:
                c.id = existing.id
            else:
                cust_entity = Customer(
                    id=c.id, code=c.code, name=c.name, tax_id=c.tax_id,
                    original_erp_address=c.original_erp_address, normalized_address=c.normalized_address,
                    resolver_confidence=c.resolver_confidence,
                    is_generated=c.is_generated, generation_reason=c.generation_reason, source_lineage=c.source_lineage
                )
                session.add(cust_entity)
            for disp in batch.dispatches:
                if disp.customer_code == c.code:
                    disp.customer_id = c.id
            for o in batch.orders:
                if getattr(o, "customer_code", None) == c.code:
                    o.customer_id = c.id
            counts["customers"] += 1

        # 4. Vehicles
        for v in batch.vehicles:
            res = await session.execute(select(Vehicle).where(Vehicle.code == v.code))
            existing = res.scalars().first()
            if existing:
                v.id = existing.id
            else:
                veh_entity = Vehicle(
                    id=v.id, code=v.code, license_plate=v.license_plate or v.code,
                    capacity_m3=v.capacity_m3, vehicle_type=v.vehicle_type, fleet_category=v.fleet_category, ownership=v.ownership,
                    is_generated=v.is_generated, generation_reason=v.generation_reason, source_lineage=v.source_lineage
                )
                session.add(veh_entity)
            for disp in batch.dispatches:
                if disp.vehicle_code == v.code:
                    disp.vehicle_id = v.id
            for trp in batch.trips:
                if trp.vehicle_code == v.code:
                    trp.vehicle_id = v.id
            counts["vehicles"] += 1

        # 5. Drivers
        for d in batch.drivers:
            res_drv = await session.execute(select(Driver).where(Driver.employee_id == d.employee_id))
            existing_drv = res_drv.scalars().first()
            if existing_drv:
                d.id = existing_drv.id
            else:
                drv_entity = Driver(
                    id=d.id,
                    employee_id=d.employee_id,
                    name=d.name,
                    license_number=d.license_number,
                    is_generated=d.is_generated,
                    generation_reason=d.generation_reason,
                    source_lineage=d.source_lineage,
                )
                session.add(drv_entity)
            for disp in batch.dispatches:
                if disp.driver_employee_id == d.employee_id:
                    disp.driver_id = d.id
            counts["drivers"] += 1

        await session.flush()

        # 6. Orders
        for o in batch.orders:
            res = await session.execute(select(Order).where(Order.order_number == o.order_number))
            existing = res.scalars().first()
            if existing:
                o.id = existing.id
            else:
                ord_entity = Order(
                    id=o.id,
                    order_number=o.order_number,
                    customer_id=o.customer_id,
                    order_date=o.order_date,
                    is_generated=o.is_generated,
                    generation_reason=o.generation_reason,
                    source_lineage=o.source_lineage,
                )
                session.add(ord_entity)
            for t in batch.tickets:
                if t.order_number == o.order_number:
                    t.order_id = o.id
            counts["orders"] += 1

        await session.flush()

        # 7. Tickets
        for t in batch.tickets:
            res = await session.execute(select(Ticket).where(Ticket.ticket_number == t.ticket_number))
            existing = res.scalars().first()
            if existing:
                t.id = existing.id
            else:
                tck_entity = Ticket(
                    id=t.id,
                    ticket_number=t.ticket_number,
                    order_id=t.order_id or (batch.orders[0].id if batch.orders else None),
                    plant_id=getattr(t, 'plant_id', None) or (batch.plants[0].id if batch.plants else None),
                    ticket_date=t.ticket_date,
                    is_generated=t.is_generated,
                    generation_reason=t.generation_reason,
                    source_lineage=t.source_lineage,
                )
                session.add(tck_entity)
            for disp in batch.dispatches:
                if disp.ticket_number == t.ticket_number:
                    disp.ticket_id = t.id
            counts["tickets"] += 1

        # 8. Dispatches
        for disp in batch.dispatches:
            res = await session.execute(select(Dispatch).where(Dispatch.dispatch_number == disp.dispatch_number))
            existing = res.scalars().first()
            if existing:
                disp.id = existing.id
                if disp.t1_transit_mins is not None:
                    existing.t1_transit_mins = disp.t1_transit_mins
                    existing.t2a_holding_mins = disp.t2a_holding_mins
                    existing.t2b_unloading_mins = disp.t2b_unloading_mins
                    existing.unloading_duration_mins = disp.unloading_duration_mins
                    existing.t2c_retention_mins = disp.t2c_retention_mins
                    existing.t3_return_mins = disp.t3_return_mins
                    existing.time_out = disp.time_out
                    existing.time_in = disp.time_in
                    existing.distance_km = disp.distance_km
                if disp.import_batch_id:
                    existing.import_batch_id = disp.import_batch_id
                if disp.checksum:
                    existing.checksum = disp.checksum
                if disp.excel_row is not None:
                    existing.excel_row = disp.excel_row
                existing.version_id = (existing.version_id or 1) + 1
                counts["dispatches_updated"] += 1
            else:
                disp_entity = Dispatch(
                    id=disp.id,
                    dispatch_number=disp.dispatch_number,
                    ticket_id=disp.ticket_id,
                    vehicle_id=disp.vehicle_id,
                    driver_id=disp.driver_id,
                    plant_id=disp.plant_id,
                    customer_id=disp.customer_id,
                    dispatch_date=disp.dispatch_date,
                    time_out=disp.time_out,
                    date_in=disp.date_in,
                    time_in=disp.time_in,
                    t1_transit_mins=disp.t1_transit_mins,
                    t2a_holding_mins=disp.t2a_holding_mins,
                    t2b_unloading_mins=disp.t2b_unloading_mins,
                    unloading_duration_mins=disp.unloading_duration_mins,
                    t2c_retention_mins=disp.t2c_retention_mins,
                    t3_return_mins=disp.t3_return_mins,
                    cycle_time=disp.cycle_time,
                    distance_km=disp.distance_km,
                    status=disp.status,
                    is_generated=disp.is_generated,
                    generation_reason=disp.generation_reason,
                    source_lineage=disp.source_lineage,
                    import_batch_id=disp.import_batch_id,
                    parser_version=disp.parser_version,
                    source_system=disp.source_system,
                    excel_row=disp.excel_row,
                    checksum=disp.checksum,
                    telemetry_matched=disp.telemetry_matched,
                    telemetry_match_score=disp.telemetry_match_score,
                )
                session.add(disp_entity)
                counts["dispatches_inserted"] += 1
            for trp in batch.trips:
                if trp.dispatch_number == disp.dispatch_number:
                    trp.dispatch_id = disp.id
            counts["dispatches"] += 1

        # 9. Invoices
        for inv in batch.invoices:
            res = await session.execute(select(Invoice).where(Invoice.invoice_number == inv.invoice_number))
            existing = res.scalars().first()
            if existing:
                inv.id = existing.id
            else:
                inv_entity = Invoice(
                    id=inv.id,
                    invoice_number=inv.invoice_number,
                    customer_id=inv.customer_id,
                    total_amount=inv.total_amount,
                    invoice_date=inv.invoice_date,
                    is_generated=inv.is_generated,
                    generation_reason=inv.generation_reason,
                    source_lineage=inv.source_lineage,
                )
                session.add(inv_entity)
            counts["invoices"] += 1

        # Flush dispatches so foreign key exists for trips
        await session.flush()

        # 10. Trips
        for trp in batch.trips:
            res = await session.execute(select(Trip).where(Trip.trip_number == trp.trip_number))
            existing = res.scalars().first()
            if existing:
                trp.id = existing.id
                if trp.distance_km is not None:
                    existing.distance_km = trp.distance_km
                counts["trips_updated"] += 1
            else:
                trp_entity = Trip(
                    id=trp.id,
                    trip_number=trp.trip_number,
                    dispatch_id=trp.dispatch_id,
                    vehicle_id=trp.vehicle_id,
                    departure_time=trp.start_time,
                    arrival_time=trp.end_time,
                    distance_km=trp.distance_km,
                    is_generated=trp.is_generated,
                    generation_reason=trp.generation_reason,
                    source_lineage=trp.source_lineage,
                )
                session.add(trp_entity)
                counts["trips_inserted"] += 1
            counts["trips"] += 1

        await session.flush()
        return counts
        return counts
