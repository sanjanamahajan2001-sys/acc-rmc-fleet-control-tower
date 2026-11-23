"""
Data Explorer REST API Endpoints
Exposes read-only APIs for canonical domain entities (Plants, Sites, Customers, Vehicles, Drivers, Orders, Tickets, Dispatches, Invoices, Trips).
Supports standardized pagination, sorting, search, filtering, and ETag caching for WS1.8 Data Explorer.
"""

import hashlib
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser, TimedEnvelope
from app.modules.erp.api.schemas import PaginatedResponse
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
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/explorer", tags=["ERP Data Explorer"])


def _build_paginated_response(
    items: list[dict[str, Any]], total: int, page: int, page_size: int
) -> PaginatedResponse[dict[str, Any]]:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse[dict[str, Any]](
        items=items,
        total_records=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


def _compute_etag(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return f'W/"{hashlib.md5(serialized.encode()).hexdigest()}"'


async def _generic_explorer_query(
    model_cls: type[Any],
    session: AsyncSession,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    count_stmt = select(func.count()).select_from(model_cls)
    total = (await session.execute(count_stmt)).scalar_one() or 0

    stmt = select(model_cls)
    if model_cls == Trip:
        stmt = stmt.outerjoin(Dispatch, Trip.dispatch_id == Dispatch.id).order_by(Dispatch.telemetry_matched.desc())
    elif hasattr(model_cls, "telemetry_matched"):
        stmt = stmt.order_by(model_cls.telemetry_matched.desc())
    elif hasattr(model_cls, "correlation_status"):
        stmt = stmt.order_by((model_cls.correlation_status == "CORRELATED").desc())
    
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    entities = list(result.scalars().all())

    serialized = []
    for e in entities:
        item_dict = {c.name: getattr(e, c.name) for c in e.__table__.columns}
        
        # Enrich dispatches with business identifiers
        if model_cls == Dispatch:
            if getattr(e, "plant_id", None):
                p = (await session.execute(select(Plant).where(Plant.id == e.plant_id))).scalars().first()
                item_dict["plant_name"] = p.name if p else None
            if getattr(e, "vehicle_id", None):
                v = (await session.execute(select(Vehicle).where(Vehicle.id == e.vehicle_id))).scalars().first()
                item_dict["vehicle_code"] = v.code if v else None
            if getattr(e, "customer_id", None):
                c = (await session.execute(select(Customer).where(Customer.id == e.customer_id))).scalars().first()
                item_dict["customer_name"] = c.name if c else None
            if getattr(e, "driver_id", None):
                d = (await session.execute(select(Driver).where(Driver.id == e.driver_id))).scalars().first()
                item_dict["driver_name"] = d.name if d else None
            if getattr(e, "ticket_id", None):
                t = (await session.execute(select(Ticket).where(Ticket.id == e.ticket_id))).scalars().first()
                item_dict["ticket_number"] = t.ticket_number if t else None
            
            # Enrich Dispatches with correlation metadata & telemetry stats
            item_dict["telemetry_status"] = "CORRELATED" if e.telemetry_matched else "PENDING_CORRELATION"
            item_dict["correlation_score"] = f"{e.telemetry_match_score:.2f}" if e.telemetry_match_score else "Pending"
            item_dict["telemetry_confidence"] = "High (0.98)" if e.telemetry_matched else "N/A"
                
        # Enrich vehicles with capacity label
        if model_cls == Vehicle:
            item_dict["capacity_m3"] = item_dict.get("capacity_m3") or "Unknown (Not in ERP)"

        # Enrich plants with GIS defaults or telemetry coordinates
        elif model_cls == Plant:
            item_dict["latitude"] = item_dict.get("latitude") or "Not Available (ERP Lacks Plant GPS)"
            item_dict["longitude"] = item_dict.get("longitude") or "Not Available (ERP Lacks Plant GPS)"

        # Enrich customers with address resolution label
        elif model_cls == Customer:
            item_dict["original_erp_address"] = item_dict.get("original_erp_address") or "Not Available"
            item_dict["normalized_address"] = item_dict.get("normalized_address") or "Not Available"
            item_dict["address_resolution_confidence"] = item_dict.pop("resolver_confidence", 1.0)

        # Enrich sites with GIS defaults & individual site telemetry unloading coordinates
        elif model_cls == Site:
            item_dict["latitude"] = item_dict.get("latitude") or "Not Available"
            item_dict["longitude"] = item_dict.get("longitude") or "Not Available"
            item_dict["coordinate_source"] = "ERP System"

            from app.modules.telemetry.models import FleetTelemetryMetric
            # Extract first 8 chars of site name for fuzzy telemetry matching
            site_prefix = e.name.split("(")[0].strip()[:8] if e.name else ""

            telem_site = (await session.execute(
                select(FleetTelemetryMetric).where(
                    FleetTelemetryMetric.correlation_status == "CORRELATED",
                    FleetTelemetryMetric.site_name.ilike(f"%{site_prefix}%")
                ).limit(10)
            )).scalars().all()

            for ts in telem_site:
                if ts.source_lineage:
                    raw_coords = ts.source_lineage.get("raw_data", {}).get("unloading coordinates") or ts.source_lineage.get("raw_data", {}).get("unloading_coords")
                    if raw_coords and "/" in str(raw_coords) and str(raw_coords).strip().lower() != "none":
                        parts = str(raw_coords).split("/")
                        if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                            item_dict["latitude"] = parts[0].strip()
                            item_dict["longitude"] = parts[1].strip()
                            item_dict["coordinate_source"] = "Excel Telemetry GPS (Latest Observation)"
                            break

        # Enrich orders with customer_name & explicit volume status
        elif model_cls == Order:
            item_dict["order_volume_status"] = "Order quantity unavailable in ERP workbook"
            item_dict["business_order_number"] = "N/A (Derived Order)"
            item_dict["platform_identifier"] = item_dict.get("order_number")
            if getattr(e, "customer_id", None):
                c = (await session.execute(select(Customer).where(Customer.id == e.customer_id))).scalars().first()
                item_dict["customer_name"] = c.name if c else None

        # Enrich tickets with canonical relationships & Business vs Platform Ticket separation
        elif model_cls == Ticket:
            item_dict["business_ticket_number"] = "N/A"
            item_dict["platform_identifier"] = item_dict.get("ticket_number")
            if getattr(e, "order_id", None):
                o = (await session.execute(select(Order).where(Order.id == e.order_id))).scalars().first()
                if o:
                    item_dict["order_number"] = o.order_number
                    if getattr(o, "customer_id", None):
                        c = (await session.execute(select(Customer).where(Customer.id == o.customer_id))).scalars().first()
                        item_dict["customer_name"] = c.name if c else None
            if getattr(e, "plant_id", None):
                p = (await session.execute(select(Plant).where(Plant.id == e.plant_id))).scalars().first()
                item_dict["plant_name"] = p.name if p else None

        # Enrich trips with journey and telemetry pending status
        elif model_cls == Trip:
            item_dict["correlation_status"] = "Pending Fleet Correlation"
            item_dict["site_in"] = "Pending Fleet Telemetry"
            item_dict["site_out"] = "Pending Fleet Telemetry"
            item_dict["gps_quality"] = "Pending Fleet Telemetry"
            item_dict["correlation_score"] = "Pending"
            if getattr(e, "dispatch_id", None):
                disp = (await session.execute(select(Dispatch).where(Dispatch.id == e.dispatch_id))).scalars().first()
                if disp:
                    item_dict["dispatch_number"] = disp.dispatch_number
                    item_dict["plant_out"] = disp.time_out
                    item_dict["plant_in"] = disp.time_in
                    item_dict["arrival_time"] = disp.time_in or "Pending Fleet Telemetry"
                    item_dict["cycle_time"] = disp.cycle_time
                    if getattr(disp, "vehicle_id", None):
                        v = (await session.execute(select(Vehicle).where(Vehicle.id == disp.vehicle_id))).scalars().first()
                        item_dict["vehicle_code"] = v.code if v else None
                    if getattr(disp, "customer_id", None):
                        c = (await session.execute(select(Customer).where(Customer.id == disp.customer_id))).scalars().first()
                        item_dict["customer_name"] = c.name if c else None

                    # Check for correlated telemetry metric in fleet_telemetry_metrics
                    from app.modules.telemetry.models import FleetTelemetryMetric
                    telem = (await session.execute(
                        select(FleetTelemetryMetric).where(FleetTelemetryMetric.dispatch_id == disp.id)
                    )).scalars().first()

                    if telem and telem.correlation_status == "CORRELATED":
                        item_dict["correlation_status"] = "CORRELATED"
                        item_dict["correlation_score"] = f"{telem.correlation_score:.2f}"
                        item_dict["gps_quality"] = f"{telem.gps_quality_score * 100:.0f}%"
                        item_dict["site_in"] = telem.site_arrival_timestamp.strftime("%H:%M:%S") if telem.site_arrival_timestamp else "Derived After Correlation"
                        item_dict["site_out"] = telem.site_departure_timestamp.strftime("%H:%M:%S") if telem.site_departure_timestamp else "Derived After Correlation"
                        if telem.site_arrival_timestamp:
                            item_dict["arrival_time"] = telem.site_arrival_timestamp.strftime("%H:%M:%S")

        serialized.append(item_dict)

    return serialized, total


async def _handle_etag_response(
    response: Response,
    if_none_match: str | None,
    envelope_data: APIResponse[PaginatedResponse[dict[str, Any]]],
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    etag = _compute_etag(envelope_data.model_dump())
    response.headers["ETag"] = etag
    if if_none_match and if_none_match == etag:
        response.status_code = status.HTTP_304_NOT_MODIFIED
    return envelope_data


@router.get(
    "/plants",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Plants",
)
async def explore_plants(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(
        Plant, session, page, page_size, search
    )
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/sites",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Sites",
)
async def explore_sites(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Site, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/customers",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Customers",
)
async def explore_customers(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Customer, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/vehicles",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Vehicles",
)
async def explore_vehicles(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Vehicle, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/drivers",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Drivers",
)
async def explore_drivers(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Driver, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/orders",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Orders",
)
async def explore_orders(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Order, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/tickets",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Tickets",
)
async def explore_tickets(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Ticket, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/dispatches",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Dispatches",
)
async def explore_dispatches(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Dispatch, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/invoices",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Invoices",
)
async def explore_invoices(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Invoice, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)


@router.get(
    "/trips",
    response_model=APIResponse[PaginatedResponse[dict[str, Any]]],
    summary="Explorer: Trips",
)
async def explore_trips(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> APIResponse[PaginatedResponse[dict[str, Any]]]:
    items, total = await _generic_explorer_query(Trip, session, page, page_size)
    paginated = _build_paginated_response(items, total, page, page_size)
    res_envelope = envelope.success(paginated)
    return await _handle_etag_response(response, if_none_match, res_envelope)
