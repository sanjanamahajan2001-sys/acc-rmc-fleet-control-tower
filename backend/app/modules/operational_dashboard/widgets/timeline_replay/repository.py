"""
WS-08.3 Timeline Replay Repository.
Provides database queries over dispatches, telemetry metrics, plants, sites, and operational alerts.
Supports both Plant/Customer UUIDs and Plant/Customer codes (e.g. ACC_DHARGA, CUST_A_K_MEHTA)
to seamlessly align with DashboardFilterProvider contracts.
"""
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch, Plant, Site, Customer, Vehicle

from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
from app.modules.telemetry.models import FleetTelemetryMetric


class TimelineReplayRepository:
    """
    PostgreSQL-backed Data Access Repository for WS-08 Timeline Replay.
    Uses efficient server-side pagination, indexed scope filtering (supporting UUID or code), and set-based joins (no N+1).
    """

    @classmethod
    async def _apply_scope_filters(
        cls,
        query: Any,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
    ) -> Any:
        # Plant Filter (UUID or Code e.g. ACC_DHARGA)
        if plant_id and plant_id != "ALL":
            try:
                plant_uuid = UUID(plant_id)
                query = query.where(Dispatch.plant_id == plant_uuid)
            except ValueError:
                plant_subq = select(Plant.id).where(or_(Plant.code == plant_id, Plant.name == plant_id))
                query = query.where(Dispatch.plant_id.in_(plant_subq))

        # Customer Filter (UUID or Code e.g. CUST_A_K_MEHTA)
        if customer_id and customer_id != "ALL":
            try:
                cust_uuid = UUID(customer_id)
                query = query.where(Dispatch.customer_id == cust_uuid)
            except ValueError:
                cust_subq = select(Customer.id).where(or_(Customer.code == customer_id, Customer.name == customer_id))
                query = query.where(Dispatch.customer_id.in_(cust_subq))

        # Dataset Filter (WS-08.1 Dataset Authority Contract)
        if dataset_id and dataset_id != "ALL":
            try:
                dataset_uuid = UUID(dataset_id)
                query = query.where(Dispatch.import_batch_id == dataset_uuid)
            except ValueError:
                pass

        return query

    @classmethod
    async def list_replay_dispatches(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists dispatches matching scope filters with telemetry match indication.
        Returns a tuple of (dispatch_record_dicts, total_count).
        Uses subquery EXISTS to avoid N+1 telemetry queries.
        """
        # Base query for counting & filtering
        query = select(Dispatch).where(Dispatch.is_deleted == False)
        query = await cls._apply_scope_filters(query, plant_id, customer_id, dataset_id)

        # Total Count Query
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await session.execute(count_query)
        total_count = total_res.scalar() or 0

        if total_count == 0:
            return [], 0

        # Telemetry EXISTS subquery to avoid N+1 queries
        telemetry_exists_subquery = (
            select(FleetTelemetryMetric.dispatch_id)
            .where(
                and_(
                    FleetTelemetryMetric.dispatch_id == Dispatch.id,
                    or_(
                        FleetTelemetryMetric.correlation_status == "MATCHED",
                        FleetTelemetryMetric.correlation_status == "CORRELATED"
                    )
                )
            )
            .exists()
        )

        # Outer joins for human-readable codes/names
        from app.modules.erp.models import CustomerDisplayOverride
        from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService

        eff_name = CustomerDisplayOverrideService.get_effective_name_expression()

        paginated_query = (
            select(
                Dispatch,
                telemetry_exists_subquery.label("has_telemetry"),
                Plant.code.label("plant_code"),
                Customer.code.label("customer_code"),
                Customer.name.label("raw_customer_name"),
                eff_name.label("effective_customer_name"),
                Vehicle.license_plate.label("vehicle_plate"),
            )
            .outerjoin(Plant, Dispatch.plant_id == Plant.id)
            .outerjoin(Customer, Dispatch.customer_id == Customer.id)
            .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
            .outerjoin(Vehicle, Dispatch.vehicle_id == Vehicle.id)
            .where(Dispatch.is_deleted == False)
        )
        paginated_query = await cls._apply_scope_filters(paginated_query, plant_id, customer_id, dataset_id)

        paginated_query = (
            paginated_query
            .order_by(Dispatch.dispatch_date.desc(), Dispatch.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await session.execute(paginated_query)
        rows = result.all()

        dispatch_items = []
        for dispatch_obj, has_tel, p_code, c_code, raw_cname, eff_cname, v_plate in rows:
            dispatch_items.append({
                "dispatch_id": str(dispatch_obj.id),
                "dispatch_number": dispatch_obj.dispatch_number,
                "plant_id": p_code or str(dispatch_obj.plant_id),
                "customer_id": c_code or str(dispatch_obj.customer_id),
                "raw_customer_name": raw_cname or "UNSPECIFIED CUSTOMER",
                "customer_name": eff_cname or raw_cname or "UNSPECIFIED CUSTOMER",
                "effective_customer_name": eff_cname or raw_cname or "UNSPECIFIED CUSTOMER",
                "vehicle_id": v_plate or (str(dispatch_obj.vehicle_id) if dispatch_obj.vehicle_id else "N/A"),
                "dispatch_date": dispatch_obj.dispatch_date,
                "status": dispatch_obj.status,
                "has_telemetry": bool(has_tel)
            })

        return dispatch_items, total_count


    @classmethod
    async def get_dispatch_detail_data(
        cls,
        session: AsyncSession,
        dispatch_id: UUID,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
    ) -> Optional[Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]]:
        """
        Retrieves detailed dispatch, telemetry, plant, site, and correlated alert count for a dispatch.
        Enforces strict plant, customer, and dataset scope isolation. Returns None if scope check fails.
        """
        disp_query = select(Dispatch).where(and_(Dispatch.id == dispatch_id, Dispatch.is_deleted == False))
        disp_query = await cls._apply_scope_filters(disp_query, plant_id, customer_id, dataset_id)

        disp_res = await session.execute(disp_query)
        dispatch_obj = disp_res.scalar_one_or_none()

        if not dispatch_obj:
            return None

        # Resolve Customer & Effective Display Name
        from app.modules.erp.models import Customer, CustomerDisplayOverride
        from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService

        eff_name_expr = CustomerDisplayOverrideService.get_effective_name_expression()
        cust_info = (await session.execute(
            select(
                Customer.name.label("raw_name"),
                eff_name_expr.label("eff_name")
            ).outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
            .where(Customer.id == dispatch_obj.customer_id)
        )).first()

        raw_cname = cust_info.raw_name if cust_info else "UNSPECIFIED CUSTOMER"
        eff_cname = cust_info.eff_name if cust_info else raw_cname

        # Convert Dispatch model to dict
        dispatch_dict = {
            "id": dispatch_obj.id,
            "dispatch_number": dispatch_obj.dispatch_number,
            "plant_id": dispatch_obj.plant_id,
            "customer_id": dispatch_obj.customer_id,
            "raw_customer_name": raw_cname,
            "customer_name": eff_cname,
            "effective_customer_name": eff_cname,
            "vehicle_id": dispatch_obj.vehicle_id,
            "import_batch_id": dispatch_obj.import_batch_id,
            "dispatch_date": dispatch_obj.dispatch_date,
            "time_out": dispatch_obj.time_out,
            "time_in": dispatch_obj.time_in,
            "status": dispatch_obj.status,
            "t1_transit_mins": dispatch_obj.t1_transit_mins,
            "t2a_holding_mins": dispatch_obj.t2a_holding_mins,
            "t2b_unloading_mins": dispatch_obj.t2b_unloading_mins,
            "t2c_retention_mins": dispatch_obj.t2c_retention_mins,
            "t3_return_mins": dispatch_obj.t3_return_mins,
        }

        # Fetch Telemetry
        tel_query = select(FleetTelemetryMetric).where(FleetTelemetryMetric.dispatch_id == dispatch_id)
        tel_res = await session.execute(tel_query)
        tel_obj = tel_res.scalars().first()
        telemetry_dict = None
        if tel_obj:
            telemetry_dict = {
                "plant_out_timestamp": tel_obj.plant_out_timestamp,
                "site_arrival_timestamp": tel_obj.site_arrival_timestamp,
                "unloading_start_timestamp": tel_obj.unloading_start_timestamp,
                "unloading_end_timestamp": tel_obj.unloading_end_timestamp,
                "plant_return_timestamp": tel_obj.plant_return_timestamp,
                "avg_speed_kmh": tel_obj.avg_speed_kmh,
                "max_speed_kmh": tel_obj.max_speed_kmh,
                "drum_rotation_rpm": tel_obj.drum_rotation_rpm,
                "correlation_status": tel_obj.correlation_status,
            }

        # Fetch Plant
        plant_dict = None
        if dispatch_obj.plant_id:
            plant_res = await session.execute(select(Plant).where(Plant.id == dispatch_obj.plant_id))
            plant_obj = plant_res.scalar_one_or_none()
            if plant_obj:
                plant_dict = {
                    "id": plant_obj.id,
                    "name": plant_obj.name,
                    "latitude": plant_obj.latitude,
                    "longitude": plant_obj.longitude,
                }

        # Fetch Site (via Plant)
        site_dict = None
        if dispatch_obj.plant_id:
            site_res = await session.execute(select(Site).where(Site.plant_id == dispatch_obj.plant_id))
            site_obj = site_res.scalars().first()
            if site_obj:
                site_dict = {
                    "id": site_obj.id,
                    "name": site_obj.name,
                    "latitude": site_obj.latitude,
                    "longitude": site_obj.longitude,
                }

        # Fetch Correlated WS-07 Alerts Count (Read-Only)
        alert_count_query = select(func.count()).where(OperationalAlertModel.dispatch_id == dispatch_id)
        alert_count_res = await session.execute(alert_count_query)
        alert_count = alert_count_res.scalar() or 0

        return dispatch_dict, telemetry_dict, plant_dict, site_dict, alert_count
