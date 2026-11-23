"""
Three-Layer Verification Test Suite for WS1.1 ERP Models & Repositories
Layer 1: Unit Tests (Mock Sessions)
Layer 2: Integration Tests (Real PostgreSQL Database & Transaction Rollback)
Layer 3: Schema Constraints & Cascade Policy Verification
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.erp.models import (
    Customer,
    Dispatch,
    Driver,
    ImportAuditLog,
    ImportJob,
    ImportStatistic,
    Invoice,
    Material,
    Order,
    Plant,
    Product,
    Route,
    Site,
    Ticket,
    Trip,
    Vehicle,
    WorkbookMetadata,
)
from app.modules.erp.repositories import (
    CustomerRepository,
    DispatchRepository,
    DriverRepository,
    ImportJobRepository,
    InvoiceRepository,
    MaterialRepository,
    OrderRepository,
    PlantRepository,
    ProductRepository,
    RouteRepository,
    SiteRepository,
    TicketRepository,
    TripRepository,
    VehicleRepository,
)
from app.modules.erp.schemas import (
    DispatchSchema,
    ImportJobSchema,
    PlantSchema,
)

# =============================================================================
# LAYER 2 & 3 FIXTURES (Real PostgreSQL Integration with Transaction Rollback)
# =============================================================================


@pytest_asyncio.fixture
async def db_session():
    """
    Real PostgreSQL AsyncSession fixture.
    Runs each test inside a nested transaction that is automatically rolled back,
    ensuring 100% database isolation without state leakage across test runs.
    """
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)

    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()

    await engine.dispose()


# =============================================================================
# LAYER 1: UNIT TESTS (Mock AsyncSession)
# =============================================================================


@pytest.mark.asyncio
async def test_layer1_plant_repository_unit():
    mock_session = AsyncMock()
    repo = PlantRepository(mock_session)

    now = datetime.now(timezone.utc)
    plant = Plant(
        id=uuid.uuid4(),
        code="P_MOCK_01",
        name="Mock Plant",
        location="Industrial Zone",
        created_at=now,
        updated_at=now,
    )

    mock_result = MagicMock()
    mock_result.scalars().first.return_value = plant
    mock_session.execute.return_value = mock_result

    await repo.create(plant)
    mock_session.add.assert_called_once_with(plant)

    plant_dto = PlantSchema.model_validate(plant)
    assert plant_dto.code == "P_MOCK_01"

    fetched = await repo.get_by_code("P_MOCK_01")
    assert fetched is not None
    assert fetched.name == "Mock Plant"


@pytest.mark.asyncio
async def test_layer1_all_repositories_instantiation():
    mock_session = AsyncMock()

    plant_repo = PlantRepository(mock_session)
    site_repo = SiteRepository(mock_session)
    cust_repo = CustomerRepository(mock_session)
    mat_repo = MaterialRepository(mock_session)
    prod_repo = ProductRepository(mock_session)
    veh_repo = VehicleRepository(mock_session)
    drv_repo = DriverRepository(mock_session)
    route_repo = RouteRepository(mock_session)
    order_repo = OrderRepository(mock_session)
    ticket_repo = TicketRepository(mock_session)
    dispatch_repo = DispatchRepository(mock_session)
    invoice_repo = InvoiceRepository(mock_session)
    trip_repo = TripRepository(mock_session)
    job_repo = ImportJobRepository(mock_session)

    assert plant_repo.model_cls == Plant
    assert site_repo.model_cls == Site
    assert cust_repo.model_cls == Customer
    assert mat_repo.model_cls == Material
    assert prod_repo.model_cls == Product
    assert veh_repo.model_cls == Vehicle
    assert drv_repo.model_cls == Driver
    assert route_repo.model_cls == Route
    assert order_repo.model_cls == Order
    assert ticket_repo.model_cls == Ticket
    assert dispatch_repo.model_cls == Dispatch
    assert invoice_repo.model_cls == Invoice
    assert trip_repo.model_cls == Trip
    assert job_repo.model_cls == ImportJob


# =============================================================================
# LAYER 2: INTEGRATION TESTS (Real PostgreSQL Database & Persistence)
# =============================================================================


@pytest.mark.asyncio
async def test_layer2_plant_repository_real_db(db_session: AsyncSession):
    repo = PlantRepository(db_session)
    unique_code = f"P_{uuid.uuid4().hex[:8]}"

    # 1. Create and persist
    plant = Plant(code=unique_code, name="Real PostgreSQL Plant", location="Zone A")
    await repo.create(plant)
    await db_session.flush()

    assert plant.id is not None

    # 2. Query by code
    fetched = await repo.get_by_code(unique_code)
    assert fetched is not None
    assert fetched.name == "Real PostgreSQL Plant"

    # 3. Pydantic DTO Validation
    dto = PlantSchema.model_validate(fetched)
    assert dto.code == unique_code

    # 4. Soft Delete
    fetched.is_deleted = True
    await db_session.flush()

    deleted_check = await repo.get_by_code(unique_code)
    assert deleted_check is None


@pytest.mark.asyncio
async def test_layer2_canonical_relationships_and_foreign_keys(
    db_session: AsyncSession,
):
    plant = Plant(code=f"P_{uuid.uuid4().hex[:8]}", name="North Plant")
    customer = Customer(code=f"C_{uuid.uuid4().hex[:8]}", name="Acme Builders")
    vehicle = Vehicle(
        code=f"V_{uuid.uuid4().hex[:8]}", license_plate="MX-999-DX", capacity_m3=12.0
    )
    driver = Driver(employee_id=f"E_{uuid.uuid4().hex[:8]}", name="Alice Driver")

    db_session.add_all([plant, customer, vehicle, driver])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    order = Order(
        order_number=f"ORD_{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        order_date=now,
        total_volume_m3=50.0,
    )
    db_session.add(order)
    await db_session.flush()

    ticket = Ticket(
        ticket_number=f"TCK_{uuid.uuid4().hex[:8]}",
        order_id=order.id,
        plant_id=plant.id,
        ticket_date=now,
        delivered_volume_m3=10.0,
    )
    db_session.add(ticket)
    await db_session.flush()

    dispatch = Dispatch(
        dispatch_number=f"DSP_{uuid.uuid4().hex[:8]}",
        ticket_id=ticket.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        plant_id=plant.id,
        customer_id=customer.id,
        dispatch_date=now,
        status="DISPATCHED",
    )
    db_session.add(dispatch)
    await db_session.flush()

    dispatch_repo = DispatchRepository(db_session)
    fetched = await dispatch_repo.get_by_dispatch_number(dispatch.dispatch_number)
    assert fetched is not None
    assert fetched.status == "DISPATCHED"
    assert fetched.plant_id == plant.id
    assert fetched.customer_id == customer.id

    dto = DispatchSchema.model_validate(fetched)
    assert dto.dispatch_number == dispatch.dispatch_number


@pytest.mark.asyncio
async def test_layer2_all_repositories_crud_real_db(db_session: AsyncSession):
    site_repo = SiteRepository(db_session)
    cust_repo = CustomerRepository(db_session)
    mat_repo = MaterialRepository(db_session)
    prod_repo = ProductRepository(db_session)
    veh_repo = VehicleRepository(db_session)
    drv_repo = DriverRepository(db_session)
    route_repo = RouteRepository(db_session)
    order_repo = OrderRepository(db_session)
    ticket_repo = TicketRepository(db_session)
    invoice_repo = InvoiceRepository(db_session)
    trip_repo = TripRepository(db_session)

    suffix = uuid.uuid4().hex[:8]
    plant = Plant(code=f"P_{suffix}", name="South Plant")
    db_session.add(plant)
    await db_session.flush()

    site = Site(code=f"S_{suffix}", name="Bay Tower", plant_id=plant.id)
    customer = Customer(code=f"C_{suffix}", name="BuildCorp")
    material = Material(code=f"M_{suffix}", name="Sand 5mm")
    product = Product(code=f"PR_{suffix}", name="C25 Concrete")
    vehicle = Vehicle(code=f"V_{suffix}", license_plate="MX-111-DX")
    driver = Driver(employee_id=f"E_{suffix}", name="Bob Driver")

    db_session.add_all([site, customer, material, product, vehicle, driver])
    await db_session.flush()

    assert await site_repo.get_by_id(site.id) is not None
    assert await cust_repo.get_by_code(customer.code) is not None
    assert await mat_repo.get_by_id(material.id) is not None
    assert await prod_repo.get_by_id(product.id) is not None
    assert await veh_repo.get_by_id(vehicle.id) is not None
    assert await drv_repo.get_by_id(driver.id) is not None

    route = Route(
        code=f"R_{suffix}", origin_plant_id=plant.id, destination_site_id=site.id
    )
    db_session.add(route)
    await db_session.flush()
    assert await route_repo.get_by_id(route.id) is not None

    now = datetime.now(timezone.utc)
    order = Order(order_number=f"ORD_{suffix}", customer_id=customer.id, order_date=now)
    db_session.add(order)
    await db_session.flush()
    assert await order_repo.get_by_id(order.id) is not None

    ticket = Ticket(
        ticket_number=f"TCK_{suffix}",
        order_id=order.id,
        plant_id=plant.id,
        ticket_date=now,
    )
    invoice = Invoice(
        invoice_number=f"INV_{suffix}", customer_id=customer.id, invoice_date=now
    )
    db_session.add_all([ticket, invoice])
    await db_session.flush()

    assert await ticket_repo.get_by_id(ticket.id) is not None
    assert await invoice_repo.get_by_id(invoice.id) is not None

    dispatch = Dispatch(
        dispatch_number=f"DSP_{suffix}",
        ticket_id=ticket.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        plant_id=plant.id,
        customer_id=customer.id,
        dispatch_date=now,
    )
    db_session.add(dispatch)
    await db_session.flush()

    trip = Trip(
        trip_number=f"TRP_{suffix}", dispatch_id=dispatch.id, departure_time=now
    )
    db_session.add(trip)
    await db_session.flush()
    assert await trip_repo.get_by_id(trip.id) is not None


@pytest.mark.asyncio
async def test_layer2_import_job_metadata_cascade_real_db(db_session: AsyncSession):
    job_repo = ImportJobRepository(db_session)
    job_num = f"JOB_{uuid.uuid4().hex[:8]}"

    job = ImportJob(
        job_number=job_num,
        status="QUEUED",
        file_name="dispatches_2026.xlsx",
        file_hash="hash_1234567890",
        total_rows=500,
        processed_rows=0,
        error_count=0,
    )
    db_session.add(job)
    await db_session.flush()

    wb_meta = WorkbookMetadata(
        job_id=job.id, sheet_names=["Dispatches"], schema_version="v2.0"
    )
    audit = ImportAuditLog(job_id=job.id, action="JOB_INITIALIZED")
    stat = ImportStatistic(
        job_id=job.id, duration_ms=100.0, rows_per_sec=50.0, peak_memory_mb=30.0
    )

    db_session.add_all([wb_meta, audit, stat])
    await db_session.flush()

    fetched = await job_repo.get_by_job_number(job_num)
    assert fetched is not None
    assert fetched.file_name == "dispatches_2026.xlsx"

    dto = ImportJobSchema.model_validate(fetched)
    assert dto.job_number == job_num


# =============================================================================
# LAYER 3: CONSTRAINTS & CASCADE POLICIES (Unique Indexes & Foreign Keys)
# =============================================================================


@pytest.mark.asyncio
async def test_layer3_unique_constraint_enforcement(db_session: AsyncSession):
    code = f"P_DUP_{uuid.uuid4().hex[:6]}"
    p1 = Plant(code=code, name="Plant One")
    db_session.add(p1)
    await db_session.flush()

    nested = await db_session.begin_nested()
    try:
        p2 = Plant(code=code, name="Plant Two Duplicate")
        db_session.add(p2)
        await db_session.flush()
    except IntegrityError:
        await nested.rollback()
        assert True
    else:
        pytest.fail("Should have raised IntegrityError for duplicate unique constraint")


@pytest.mark.asyncio
async def test_layer3_foreign_key_on_delete_restrict_enforcement(
    db_session: AsyncSession,
):
    plant_id = uuid.uuid4()
    site_id = uuid.uuid4()
    plant_code = f"P_{uuid.uuid4().hex[:6]}"
    site_code = f"S_{uuid.uuid4().hex[:6]}"

    # Insert raw plant & site via SQL to test database-level FK RESTRICT behavior without ORM cascade intervention
    await db_session.execute(
        text(
            "INSERT INTO plants (id, code, name, is_deleted) VALUES (:id, :code, :name, false)"
        ),
        {"id": plant_id, "code": plant_code, "name": "FK Plant"},
    )
    await db_session.execute(
        text(
            "INSERT INTO sites (id, code, name, plant_id, is_deleted) VALUES (:id, :code, :name, :plant_id, false)"
        ),
        {"id": site_id, "code": site_code, "name": "FK Site", "plant_id": plant_id},
    )
    await db_session.flush()

    nested = await db_session.begin_nested()
    try:
        await db_session.execute(
            text("DELETE FROM plants WHERE id = :id"), {"id": plant_id}
        )
        await db_session.flush()
    except IntegrityError:
        await nested.rollback()
        assert True
    else:
        pytest.fail(
            "Should have raised IntegrityError due to ON DELETE RESTRICT FK constraint"
        )


@pytest.mark.asyncio
async def test_layer3_import_job_on_delete_cascade_enforcement(
    db_session: AsyncSession,
):
    job = ImportJob(
        job_number=f"JOB_{uuid.uuid4().hex[:6]}",
        status="QUEUED",
        file_name="test.xlsx",
        file_hash="hash_abc",
        total_rows=10,
        processed_rows=0,
        error_count=0,
    )
    db_session.add(job)
    await db_session.flush()

    meta = WorkbookMetadata(
        job_id=job.id, sheet_names=["Sheet1"], schema_version="v1.0"
    )
    db_session.add(meta)
    await db_session.flush()

    meta_id = meta.id

    # Delete parent job (CASCADE policy must automatically delete child metadata)
    await db_session.delete(job)
    await db_session.flush()

    res = await db_session.execute(
        text("SELECT id FROM workbook_metadata WHERE id = :id"), {"id": meta_id}
    )
    assert res.scalar_one_or_none() is None
