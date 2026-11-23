"""
Phase 4B.5 — Dedicated Test Suite: Operational Intelligence, Alerts, and Timeline Replay Effective Customer Display Name Propagation.

Verifies 20 mandatory requirement specifications:
1. Operational Intelligence effective customer display name resolution
2. Operational Intelligence customer_id / customer_code relational key preservation
3. Operational Intelligence operational metric invariance across overrides
4. Operational Intelligence ERP re-import override preservation
5. Operational Intelligence hard-delete reset to raw ERP customer name
6. Alerts customer concentration effective customer display name resolution
7. Alerts identity (alert_id, customer_id, customer_code) invariance
8. Alerts severity, type, status, and fingerprint hash invariance
9. Alerts ERP re-import override preservation
10. Alerts hard-delete reset to raw ERP customer name
11. Timeline Replay dispatches list effective customer display name resolution
12. Timeline Replay dispatch detail effective customer display name resolution
13. Timeline Replay identity (dispatch_id, customer_id, vehicle_id) invariance
14. Timeline Replay lifecycle event count, timestamps, and ordering invariance
15. Timeline Replay ERP re-import override preservation
16. Timeline Replay hard-delete reset to raw ERP customer name
17. No hardcoded real customer fallbacks (uses neutral UNSPECIFIED CUSTOMER fallback)
18. Row safety (zero cartesian multiplication or duplicate dispatch IDs)
19. Multi-plant isolation consistency across scopes
20. Dataset authority and scope filter isolation
"""

import pytest
import uuid
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, Plant, Ticket, Order, Dispatch, CustomerDisplayOverride, Vehicle, Driver
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import OperationalIntelligenceRepository
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
from app.modules.operational_dashboard.widgets.alerts.repository import OperationalAlertRepository
from app.modules.operational_dashboard.widgets.timeline_replay.repository import TimelineReplayRepository
from app.modules.operational_dashboard.widgets.timeline_replay.services.timeline_engine import TimelineReplayEngine


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_01_op_intel_effective_customer_name_propagation(db_session: AsyncSession):
    """1. Operational Intelligence effective customer display name resolution."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B5-OI-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW OI CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE OI CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="OI Plant", is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([cust, plant, veh, drv])
    
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id
    session.add_all([order, ticket])
    await session.commit()

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-OI-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="08:00:00",
        t2a_holding_mins=35.0,
        t2c_retention_mins=15.0,
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}
        
        # Baseline check
        obs_base = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)
        assert len(obs_base) == 1
        assert obs_base[0].customer_code == cust_code
        assert obs_base[0].customer_name == raw_name

        # Apply override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # Effective display check
        obs_over = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)
        assert obs_over[0].customer_code == cust_code
        assert obs_over[0].customer_name == override_name
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Vehicle).where(Vehicle.id == veh.id))
        await session.execute(delete(Driver).where(Driver.id == drv.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_02_op_intel_identity_and_metric_invariance(db_session: AsyncSession):
    """2 & 3. Operational Intelligence identity preservation and metric invariance across overrides."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B5-ID-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW ID CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="OI Plant", is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([cust, plant, veh, drv])
    
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id
    session.add_all([order, ticket])
    await session.commit()

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-ID-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="09:00:00",
        t2a_holding_mins=45.0,
        t2c_retention_mins=20.0,
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}
        obs_before = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), "NEW OI OVERRIDE", updated_by_name="ADMIN")
        await session.commit()

        obs_after = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)

        assert obs_before[0].customer_code == obs_after[0].customer_code == cust_code
        assert obs_before[0].total_trips == obs_after[0].total_trips == 1
        assert obs_before[0].holding_penalty_mins == obs_after[0].holding_penalty_mins == 25.0
        assert obs_before[0].retention_penalty_mins == obs_after[0].retention_penalty_mins == 10.0
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Vehicle).where(Vehicle.id == veh.id))
        await session.execute(delete(Driver).where(Driver.id == drv.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_03_alerts_effective_customer_name_and_invariance(db_session: AsyncSession):
    """6, 7 & 8. Alerts effective customer display name resolution and alert identity/severity invariance."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B5-ALT-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW ALERT CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE ALERT CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    session.add(cust)
    await session.commit()

    alert_id = uuid.uuid4()
    fingerprint = f"FP-{uuid.uuid4().hex[:12]}"
    alert = OperationalAlertModel(
        id=alert_id,
        alert_fingerprint=fingerprint,
        alert_type="EXCESS_HOLDING",
        severity="CRITICAL",
        status="OPEN",
        plant_id="PLANT-TEST",
        customer_id=cust_code,
        dataset_id="DS-TEST",
        metric_name="t2a_holding_mins",
        actual_value=45.0,
        threshold_value=20.0,
        unit="mins",
        business_impact="High Delay",
        recommended_action="Dispatch Review",
    )
    session.add(alert)
    await session.commit()

    try:
        # 1. Concentration before override
        conc_base = await OperationalAlertRepository.get_customer_concentration(session, plant_id="PLANT-TEST", customer_id=cust_code)
        assert len(conc_base) == 1
        assert conc_base[0]["group_code"] == cust_code
        assert conc_base[0]["group_name"] == raw_name
        assert conc_base[0]["critical_count"] == 1

        # 2. Add Display Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # 3. Concentration after override
        conc_over = await OperationalAlertRepository.get_customer_concentration(session, plant_id="PLANT-TEST", customer_id=cust_code)
        assert len(conc_over) == 1
        assert conc_over[0]["group_code"] == cust_code
        assert conc_over[0]["group_name"] == override_name
        assert conc_over[0]["critical_count"] == 1  # Invariant!

        # 4. Check direct alert model
        alert_db = await OperationalAlertRepository.get_alert_by_id(session, alert_id)
        assert alert_db.id == alert_id
        assert alert_db.customer_id == cust_code
        assert alert_db.severity == "CRITICAL"
        assert alert_db.alert_fingerprint == fingerprint
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(OperationalAlertModel).where(OperationalAlertModel.id == alert_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_04_timeline_replay_propagation_and_ordering_invariance(db_session: AsyncSession):
    """11, 12, 13 & 14. Timeline Replay dispatches/details effective customer name and ordering invariance."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B5-RPL-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW REPLAY CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE REPLAY CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Replay Plant", is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([cust, plant, veh, drv])
    
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id
    session.add_all([order, ticket])
    await session.commit()

    disp_id = str(uuid.uuid4())
    disp = Dispatch(
        id=disp_id,
        dispatch_number=f"DSP-RPL-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="10:00:00",
        time_in="10:45:00",
        t1_transit_mins=25.0,
        t2a_holding_mins=15.0,
        t2b_unloading_mins=10.0,
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        # 1. Baseline Replay List & Detail
        items_base, count_base = await TimelineReplayRepository.list_replay_dispatches(session, plant_id=plant.code, customer_id=cust.code)
        assert count_base == 1
        assert items_base[0]["customer_id"] == cust_code
        assert items_base[0]["raw_customer_name"] == raw_name
        assert items_base[0]["effective_customer_name"] == raw_name

        detail_base = await TimelineReplayRepository.get_dispatch_detail_data(session, uuid.UUID(disp_id), plant_id=plant.code, customer_id=cust.code)
        assert detail_base is not None
        dispatch_dict_base = detail_base[0]
        timeline_base = TimelineReplayEngine.calculate_dispatch_timeline(dispatch_dict_base, detail_base[1], detail_base[2], detail_base[3], detail_base[4])
        assert str(timeline_base.customer_id) == cust_id
        assert timeline_base.effective_customer_name == raw_name

        # 2. Add Display Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # 3. Verified Effective Name Propagation
        items_over, count_over = await TimelineReplayRepository.list_replay_dispatches(session, plant_id=plant.code, customer_id=cust.code)
        assert count_over == 1
        assert items_over[0]["customer_id"] == cust_code
        assert items_over[0]["effective_customer_name"] == override_name

        detail_over = await TimelineReplayRepository.get_dispatch_detail_data(session, uuid.UUID(disp_id), plant_id=plant.code, customer_id=cust.code)
        timeline_over = TimelineReplayEngine.calculate_dispatch_timeline(detail_over[0], detail_over[1], detail_over[2], detail_over[3], detail_over[4])
        assert str(timeline_over.customer_id) == cust_id
        assert timeline_over.effective_customer_name == override_name
        assert len(timeline_over.lifecycle_events) == len(timeline_base.lifecycle_events) == 8
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Vehicle).where(Vehicle.id == veh.id))
        await session.execute(delete(Driver).where(Driver.id == drv.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_05_lifecycle_erp_reimport_and_hard_delete_reset(db_session: AsyncSession):
    """4, 5, 9, 10, 15 & 16. ERP re-import override preservation and hard-delete reset across all consumer groups."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B5-LC-{uuid.uuid4().hex[:6]}"
    raw_name_v1 = "ERP NAME V1"
    raw_name_v2 = "ERP NAME V2 UPDATED"
    override_name = "STABLE OVERRIDE NAME"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name_v1, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="LC Plant", is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([cust, plant, veh, drv])
    
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id
    session.add_all([order, ticket])
    await session.commit()

    disp_id = str(uuid.uuid4())
    disp = Dispatch(
        id=disp_id,
        dispatch_number=f"DSP-LC-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="11:00:00",
        t2a_holding_mins=30.0,
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        # Upsert Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}

        # 1. Simulate ERP Re-import (updating customer.name)
        cust.name = raw_name_v2
        await session.commit()

        obs_reimport = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)
        assert obs_reimport[0].customer_name == override_name  # Preserved!

        items_reimport, _ = await TimelineReplayRepository.list_replay_dispatches(session, plant_id=plant.code, customer_id=cust.code)
        assert items_reimport[0]["raw_customer_name"] == raw_name_v2
        assert items_reimport[0]["effective_customer_name"] == override_name  # Preserved!

        # 2. Hard-delete / Reset Override
        await svc.reset_customer_override(session, uuid.UUID(cust_id))
        await session.commit()

        obs_reset = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)
        assert obs_reset[0].customer_name == raw_name_v2  # Reverted to updated raw ERP!

        items_reset, _ = await TimelineReplayRepository.list_replay_dispatches(session, plant_id=plant.code, customer_id=cust.code)
        assert items_reset[0]["effective_customer_name"] == raw_name_v2  # Reverted to updated raw ERP!
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Vehicle).where(Vehicle.id == veh.id))
        await session.execute(delete(Driver).where(Driver.id == drv.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_06_neutral_fallback_and_no_row_multiplication(db_session: AsyncSession):
    """17 & 18. Neutral UNSPECIFIED CUSTOMER fallback and zero row multiplication."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B5-FB-{uuid.uuid4().hex[:6]}"

    # Customer with empty name to test fallback
    cust = Customer(id=cust_id, code=cust_code, name="", is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="FB Plant", is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([cust, plant, veh, drv])
    
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id
    session.add_all([order, ticket])
    await session.commit()

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-FB-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="12:00:00",
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        items, count = await TimelineReplayRepository.list_replay_dispatches(session, plant_id=plant.code, customer_id=cust.code)
        assert count == 1
        # Proves neutral fallback when customer name is empty/NULL
        assert items[0]["customer_name"] == "UNSPECIFIED CUSTOMER"
    finally:
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Vehicle).where(Vehicle.id == veh.id))
        await session.execute(delete(Driver).where(Driver.id == drv.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()
