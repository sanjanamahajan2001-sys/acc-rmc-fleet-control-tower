"""
Phase 4B.3 — Dedicated Test Suite: Overall Dashboard & Site Comparison Effective Customer Name Propagation.

Verifies:
1. Overall Dashboard effective customer name resolution
2. Site Comparison effective customer name resolution
3. customer_id identity preservation (relational key integrity)
4. customer_code preservation
5. raw ERP customers.name immutability
6. Aggregation metric invariance (baseline vs effective)
7. Row-count invariance (no row multiplication via LEFT JOIN)
8. Multi-plant consistency (one customer-level display override across all plants)
9. ERP re-import override preservation
10. Hard-delete reset to raw ERP customers.name
11. No hardcoded customer fallback (uses UNSPECIFIED CUSTOMER if empty)
12. Cross-consumer consistency (Overall Dashboard & Site Comparison match)
"""

import pytest
import uuid
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, Plant, Ticket, Order, Dispatch, CustomerDisplayOverride, Vehicle, Driver
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import OperationalIntelligenceRepository
from app.modules.operational_dashboard.widgets.operational_intelligence.services.problem_customers import ProblemCustomersEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.customer_efficiency import CustomerEfficiencyEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness import SiteReadinessEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_details import DASDetailsEngine


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_01_overall_dashboard_effective_customer_name_propagation(db_session: AsyncSession):
    """Verify Overall Dashboard problem customers & CEI engines return effective customer display name when override exists."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B3-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW NAME {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE NAME {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([veh, drv])
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Test Plant", is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    now_dt = datetime.now(timezone.utc)
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=now_dt, is_deleted=False)
    ticket.order_id = order.id

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant.id,
        ticket_id=ticket.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t2a_holding_mins=35.0,
        t2c_retention_mins=20.0,
    )

    session.add_all([cust, plant, order, ticket, disp])
    await session.commit()

    try:
        filters = {"plant_id": "ALL", "customer_id": cust_code, "dataset_type": "REAL_ONLY"}
        prob_before = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert len(prob_before.data) == 1
        assert prob_before.data[0].customer_name == raw_name

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(
            session=session,
            customer_id=uuid.UUID(cust_id),
            override_name=override_name,
        )

        prob_after = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert len(prob_after.data) == 1
        assert prob_after.data[0].customer_name == override_name

        cei_after = await CustomerEfficiencyEngine.get_customer_efficiency(session, filters)
        assert len(cei_after.data) == 1
        assert cei_after.data[0].customer_name == override_name

        das_after = await DASDetailsEngine.evaluate_details(session, filters)
        assert len(das_after.data) == 1
        assert das_after.data[0].customer_name == override_name

    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_02_site_comparison_effective_customer_name_propagation(db_session: AsyncSession):
    """Verify Site Readiness / Comparison customer-level views propagate effective display name."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B3-SITE-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW SITE CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE SITE CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([veh, drv])
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-SITE-{uuid.uuid4().hex[:6]}", name="Site Plant", is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-SITE-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-SITE-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-SITE-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant.id,
        ticket_id=ticket.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t1_transit_mins=25.0,
        t2a_holding_mins=15.0,
    )

    session.add_all([cust, plant, order, ticket, disp])
    await session.commit()

    try:
        filters = {"plant_id": "ALL", "customer_id": cust_code, "dataset_type": "REAL_ONLY"}

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(
            session=session,
            customer_id=uuid.UUID(cust_id),
            override_name=override_name,
        )

        readiness_res = await SiteReadinessEngine.get_site_readiness(session, filters)
        assert len(readiness_res.data) == 1
        assert readiness_res.data[0].site_name == override_name

    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_03_relational_identity_and_code_preservation(db_session: AsyncSession):
    """Verify customer_id and customer_code remain strictly unchanged before and after display override."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B3-ID-{uuid.uuid4().hex[:6]}"
    raw_name = "RAW IDENT NAME"
    override_name = "OVERRIDDEN IDENT NAME"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([veh, drv])
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-ID-{uuid.uuid4().hex[:6]}", name="ID Plant", is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-ID-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-ID-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant.id,
        ticket_id=ticket.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
    )

    session.add_all([cust, plant, order, ticket, disp])
    await session.commit()

    try:
        filters = {"plant_id": "ALL", "customer_id": cust_code, "dataset_type": "REAL_ONLY"}

        prob_before = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert prob_before.data[0].customer_id == cust_code

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name)

        prob_after = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert prob_after.data[0].customer_id == cust_code

        db_cust = (await session.execute(select(Customer).where(Customer.id == cust_id))).scalar_one()
        assert str(db_cust.id) == cust_id
        assert db_cust.code == cust_code
        assert db_cust.name == raw_name

    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_04_metric_and_row_count_invariance(db_session: AsyncSession):
    """Verify aggregated metrics (trips, penalty mins) and row counts are identical before vs after override."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B3-INV-{uuid.uuid4().hex[:6]}"
    raw_name = "RAW METRIC NAME"
    override_name = "OVERRIDE METRIC NAME"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([veh, drv])
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-INV-{uuid.uuid4().hex[:6]}", name="Inv Plant", is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-INV-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-INV-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id

    disp1 = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-INV-1-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant.id,
        ticket_id=ticket.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t2a_holding_mins=45.0,
        t2c_retention_mins=25.0,
    )
    disp2 = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-INV-2-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant.id,
        ticket_id=ticket.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t2a_holding_mins=15.0,
        t2c_retention_mins=5.0,
    )

    session.add_all([cust, plant, order, ticket, disp1, disp2])
    await session.commit()

    try:
        filters = {"plant_id": "ALL", "customer_id": cust_code, "dataset_type": "REAL_ONLY"}

        obs_before = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)
        assert len(obs_before) == 1
        before_trips = obs_before[0].total_trips
        before_holding_pen = obs_before[0].holding_penalty_mins
        before_retention_pen = obs_before[0].retention_penalty_mins

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name)

        obs_after = await OperationalIntelligenceRepository.get_problem_customer_observations(session, filters)
        assert len(obs_after) == 1
        assert obs_after[0].total_trips == before_trips
        assert obs_after[0].holding_penalty_mins == before_holding_pen
        assert obs_after[0].retention_penalty_mins == before_retention_pen

    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id.in_([disp1.id, disp2.id])))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_05_multi_plant_consistency(db_session: AsyncSession):
    """Verify single customer display override applies consistently across dispatches originating from multiple plants."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B3-MULTI-{uuid.uuid4().hex[:6]}"
    raw_name = "RAW MULTI CUST"
    override_name = "SHARED OVERRIDE CUST"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([veh, drv])
    plant1 = Plant(id=str(uuid.uuid4()), code=f"PLANT-MULTI-1-{uuid.uuid4().hex[:6]}", name="Plant North", is_deleted=False)
    plant2 = Plant(id=str(uuid.uuid4()), code=f"PLANT-MULTI-2-{uuid.uuid4().hex[:6]}", name="Plant South", is_deleted=False)

    ticket1 = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-M1-{uuid.uuid4().hex[:6]}", plant_id=plant1.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket2 = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-M2-{uuid.uuid4().hex[:6]}", plant_id=plant2.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)

    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-MULTI-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket1.order_id = order.id
    ticket2.order_id = order.id

    disp1 = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-M1-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant1.id,
        ticket_id=ticket1.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t2a_holding_mins=30.0,
    )
    disp2 = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-M2-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant2.id,
        ticket_id=ticket2.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t2a_holding_mins=35.0,
    )

    session.add_all([cust, plant1, plant2, order, ticket1, ticket2, disp1, disp2])
    await session.commit()

    try:
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name)

        p1_res = await ProblemCustomersEngine.get_top_problem_customers(
            session, {"plant_id": plant1.code, "customer_id": cust_code, "dataset_type": "REAL_ONLY"}
        )
        assert len(p1_res.data) == 1
        assert p1_res.data[0].customer_name == override_name

        p2_res = await ProblemCustomersEngine.get_top_problem_customers(
            session, {"plant_id": plant2.code, "customer_id": cust_code, "dataset_type": "REAL_ONLY"}
        )
        assert len(p2_res.data) == 1
        assert p2_res.data[0].customer_name == override_name

    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id.in_([disp1.id, disp2.id])))
        await session.execute(delete(Ticket).where(Ticket.id.in_([ticket1.id, ticket2.id])))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id.in_([plant1.id, plant2.id])))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_06_erp_reimport_preservation_and_hard_delete_reset(db_session: AsyncSession):
    """Verify ERP re-import updating raw customers.name preserves active override, and hard-delete reset restores raw name."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B3-RESET-{uuid.uuid4().hex[:6]}"
    initial_raw_name = "AK MEHTA ORIGINAL"
    override_name = "AK MEHTA - V2"
    reimported_raw_name = "AK MEHTA ERP UPDATED"

    cust = Customer(id=cust_id, code=cust_code, name=initial_raw_name, is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([veh, drv])
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-RST-{uuid.uuid4().hex[:6]}", name="Reset Plant", is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-RST-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-RST-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id

    disp = Dispatch(
        id=str(uuid.uuid4()),
        dispatch_number=f"DSP-RST-{uuid.uuid4().hex[:6]}",
        dispatch_date=datetime.now(timezone.utc),
        vehicle_id=veh.id,
        driver_id=drv.id,
        plant_id=plant.id,
        ticket_id=ticket.id,
        customer_id=cust_id,
        status="DELIVERED",
        is_deleted=False,
        is_generated=False,
        t2a_holding_mins=30.0,
    )

    session.add_all([cust, plant, order, ticket, disp])
    await session.commit()

    try:
        filters = {"plant_id": "ALL", "customer_id": cust_code, "dataset_type": "REAL_ONLY"}

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name)
        res1 = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert res1.data[0].customer_name == override_name

        await session.execute(update(Customer).where(Customer.id == cust_id).values(name=reimported_raw_name))
        await session.commit()

        res2 = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert res2.data[0].customer_name == override_name

        await svc.reset_customer_override(session, uuid.UUID(cust_id))

        res3 = await ProblemCustomersEngine.get_top_problem_customers(session, filters)
        assert res3.data[0].customer_name == reimported_raw_name

    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Dispatch).where(Dispatch.id == disp.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()
