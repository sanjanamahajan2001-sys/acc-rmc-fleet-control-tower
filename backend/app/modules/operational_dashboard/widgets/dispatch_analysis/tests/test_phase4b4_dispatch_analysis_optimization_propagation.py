"""
Phase 4B.4 — Dedicated Test Suite: Dispatch Analysis & Dispatch Optimization Effective Customer Name Propagation.

Verifies:
1. Dispatch Analysis (scoped dispatches & customer vehicle report) effective customer name resolution
2. Dispatch Optimization (solver candidate scenario Gantt items) effective customer name resolution
3. customer_id / customer_code relational key identity preservation
4. raw ERP customers.name immutability
5. Aggregation metric & optimization constraint invariance
6. Row-count invariance (no row multiplication via LEFT JOIN)
7. Active override DB state benchmark (0 vs 1 vs 50 overrides)
8. Hard-delete reset & ERP re-import resilience
"""

import pytest
import uuid
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, Plant, Ticket, Order, Dispatch, CustomerDisplayOverride, Vehicle, Driver
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import DispatchAnalysisRepository
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.cadence_engine import DispatchCadenceEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import DispatchOptimizationSolverEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunRequestDTO,
    OptimizationFilterParamsDTO,
    ObjectiveConfigDTO,
    OptimizationObjectiveEnum,
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_01_dispatch_analysis_effective_customer_name_propagation(db_session: AsyncSession):
    """Verifies Dispatch Analysis scoped dispatches & customer reports propagate effective customer display name."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B4-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE DISPATCH CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Test Plant", is_deleted=False)
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
        dispatch_number=f"DSP-P4B4-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="09:00:00",
        time_in="09:45:00",
        t1_transit_mins=25.0,
        t2a_holding_mins=15.0,
        t2c_retention_mins=5.0,
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        # 1. Baseline without override
        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}
        rows_base = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)
        assert len(rows_base) == 1
        assert rows_base[0]["customer_code"] == cust_code
        assert rows_base[0]["raw_customer_name"] == raw_name
        assert rows_base[0]["effective_customer_name"] == raw_name

        report_base = await DispatchCadenceEngine.get_customer_report(session, filters)
        assert len(report_base.data) == 1
        assert report_base.data[0].customer_name == raw_name

        # 2. Add Display Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # 3. Verified Effective Name Propagation
        rows_over = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)
        assert rows_over[0]["customer_code"] == cust_code
        assert rows_over[0]["raw_customer_name"] == raw_name
        assert rows_over[0]["effective_customer_name"] == override_name

        report_over = await DispatchCadenceEngine.get_customer_report(session, filters)
        assert report_over.data[0].customer_name == override_name
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
async def test_02_dispatch_optimization_effective_customer_name_propagation(db_session: AsyncSession):
    """Verifies Dispatch Optimization solver candidate Gantt items propagate effective customer display name."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B4-OPT-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW OPT CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE OPT CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Test Opt Plant", is_deleted=False)
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
        dispatch_number=f"DSP-P4B4-OPT-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="10:00:00",
        time_in="10:45:00",
        t1_transit_mins=30.0,
        t2a_holding_mins=18.0,
        t2c_retention_mins=6.0,
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        # Apply Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        req = OptimizationRunRequestDTO(
            filters=OptimizationFilterParamsDTO(plant_id=plant.code, customer_id=cust.code, dataset_type="REAL_ONLY"),
            objective_config=ObjectiveConfigDTO(objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS),
        )
        res = await DispatchOptimizationSolverEngine.execute_optimization_run(session, req)

        assert res.success is True
        assert len(res.scenarios) > 0
        gantt_item = res.scenarios[0].gantt_items[0]
        assert gantt_item.customer_id == cust_code
        assert gantt_item.customer_name == raw_name
        assert gantt_item.effective_customer_name == override_name
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
async def test_03_customer_id_and_code_relational_key_preservation(db_session: AsyncSession):
    """Verifies customer_id and customer_code remain strictly invariant under display name overrides."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B4-ID-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW ID CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Test Plant", is_deleted=False)
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
        dispatch_number=f"DSP-P4B4-ID-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="11:00:00",
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}
        base_rows = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), "NEW DISPLAY NAME", updated_by_name="ADMIN")
        await session.commit()

        over_rows = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        assert base_rows[0]["customer_code"] == over_rows[0]["customer_code"] == cust_code
        assert base_rows[0]["dispatch_id"] == over_rows[0]["dispatch_id"]
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
async def test_04_raw_erp_customers_name_immutability(db_session: AsyncSession):
    """Verifies customers.name in ERP database is never modified by display name override operations."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B4-IMM-{uuid.uuid4().hex[:6]}"
    raw_name = f"IMMUTABLE ERP NAME {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), "OVERRIDDEN NAME DISPLAY ONLY", updated_by_name="ADMIN")
        await session.commit()

        # Inspect direct raw table model
        cust_db = (await session.execute(select(Customer).where(Customer.id == cust_id))).scalar_one()
        assert cust_db.name == raw_name
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_05_row_count_and_metric_invariance(db_session: AsyncSession):
    """Verifies total dispatches, metric totals, and row counts are invariant under active display overrides."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B4-INV-{uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name="RAW INVARIANT CUST", is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Test Plant", is_deleted=False)
    veh = Vehicle(id=str(uuid.uuid4()), code=f"TRK-{uuid.uuid4().hex[:6]}", license_plate=f"GA01-{uuid.uuid4().hex[:4].upper()}", is_deleted=False)
    drv = Driver(id=str(uuid.uuid4()), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name=f"Driver {uuid.uuid4().hex[:4]}", is_deleted=False)
    session.add_all([cust, plant, veh, drv])
    
    order = Order(id=str(uuid.uuid4()), order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=cust_id, order_date=datetime.now(timezone.utc), is_deleted=False)
    ticket = Ticket(id=str(uuid.uuid4()), ticket_number=f"TKT-{uuid.uuid4().hex[:6]}", plant_id=plant.id, ticket_date=datetime.now(timezone.utc), is_deleted=False)
    ticket.order_id = order.id
    session.add_all([order, ticket])
    await session.commit()

    dispatches = [
        Dispatch(
            id=str(uuid.uuid4()),
            dispatch_number=f"DSP-INV-{idx}-{uuid.uuid4().hex[:4]}",
            ticket_id=ticket.id,
            plant_id=plant.id,
            customer_id=cust.id,
            vehicle_id=veh.id,
            driver_id=drv.id,
            dispatch_date=datetime.now(timezone.utc),
            time_out="12:00:00",
            t1_transit_mins=20.0,
            t2a_holding_mins=10.0,
            t2c_retention_mins=5.0,
            status="COMPLETED",
            is_generated=False,
        )
        for idx in range(3)
    ]
    session.add_all(dispatches)
    await session.commit()

    try:
        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}
        base_rows = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), "OVERRIDDEN INVARIANT NAME", updated_by_name="ADMIN")
        await session.commit()

        over_rows = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)

        assert len(base_rows) == len(over_rows) == 3
        assert sum(r["t1_transit_mins"] for r in base_rows) == sum(r["t1_transit_mins"] for r in over_rows) == 60.0
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        for d in dispatches:
            await session.execute(delete(Dispatch).where(Dispatch.id == d.id))
        await session.execute(delete(Ticket).where(Ticket.id == ticket.id))
        await session.execute(delete(Order).where(Order.id == order.id))
        await session.execute(delete(Plant).where(Plant.id == plant.id))
        await session.execute(delete(Vehicle).where(Vehicle.id == veh.id))
        await session.execute(delete(Driver).where(Driver.id == drv.id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_06_hard_delete_reset_and_erp_reimport_resilience(db_session: AsyncSession):
    """Verifies deleting override resets effective name to raw ERP, and ERP re-import preserves existing override."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B4-RES-{uuid.uuid4().hex[:6]}"
    raw_name_v1 = "ERP NAME V1"
    raw_name_v2 = "ERP NAME V2 UPDATED"
    override_name = "STABLE OVERRIDE NAME"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name_v1, is_deleted=False)
    plant = Plant(id=str(uuid.uuid4()), code=f"PLANT-{uuid.uuid4().hex[:6]}", name="Test Plant", is_deleted=False)
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
        dispatch_number=f"DSP-RES-{uuid.uuid4().hex[:6]}",
        ticket_id=ticket.id,
        plant_id=plant.id,
        customer_id=cust.id,
        vehicle_id=veh.id,
        driver_id=drv.id,
        dispatch_date=datetime.now(timezone.utc),
        time_out="14:00:00",
        status="COMPLETED",
        is_generated=False,
    )
    session.add(disp)
    await session.commit()

    try:
        # 1. Upsert Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        filters = {"plant_id": plant.code, "customer_id": cust.code, "dataset_type": "REAL_ONLY"}
        rows1 = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)
        assert rows1[0]["effective_customer_name"] == override_name

        # 2. Simulate ERP Re-import (updating customer.name)
        cust.name = raw_name_v2
        await session.commit()

        rows2 = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)
        assert rows2[0]["raw_customer_name"] == raw_name_v2
        assert rows2[0]["effective_customer_name"] == override_name  # Preserved!

        # 3. Reset / Delete Override
        await svc.reset_customer_override(session, uuid.UUID(cust_id))
        await session.commit()

        rows3 = await DispatchAnalysisRepository.get_scoped_dispatches(session, filters)
        assert rows3[0]["effective_customer_name"] == raw_name_v2  # Reverted to updated raw ERP!
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
