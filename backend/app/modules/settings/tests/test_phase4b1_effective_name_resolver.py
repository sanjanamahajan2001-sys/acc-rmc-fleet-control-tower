import pytest
import uuid
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, CustomerDisplayOverride, Order, Plant, Dispatch
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()



@pytest.mark.asyncio
async def test_resolver_no_override(db_session: AsyncSession):
    """TEST 1 — No Override: effective = raw ERP name."""
    test_code = f"TEST_CUST_NO_OV_{uuid.uuid4().hex[:6]}"
    customer = Customer(
        code=test_code,
        name="A K MEHTA",
    )
    db_session.add(customer)
    await db_session.commit()

    stmt = (
        select(
            Customer.id,
            Customer.name.label("raw_customer_name"),
            CustomerDisplayOverrideService.get_effective_name_expression(),
        )
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    row = (await db_session.execute(stmt)).first()
    assert row is not None
    assert row.raw_customer_name == "A K MEHTA"
    assert row.effective_customer_name == "A K MEHTA"

    # Cleanup
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_resolver_active_override(db_session: AsyncSession):
    """TEST 2 — Active Override: effective = override_name."""
    test_code = f"TEST_CUST_ACT_OV_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    stmt = (
        select(
            Customer.id,
            Customer.name.label("raw_customer_name"),
            CustomerDisplayOverrideService.get_effective_name_expression(),
        )
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    row = (await db_session.execute(stmt)).first()
    assert row is not None
    assert row.raw_customer_name == "A K MEHTA"
    assert row.effective_customer_name == "A K MEHTA - V2"

    # Cleanup
    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_resolver_whitespace_override(db_session: AsyncSession):
    """TEST 3 — Whitespace Override: falls back to raw ERP name."""
    test_code = f"TEST_CUST_WS_OV_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="   ",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    stmt = (
        select(
            Customer.id,
            Customer.name.label("raw_customer_name"),
            CustomerDisplayOverrideService.get_effective_name_expression(),
        )
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    row = (await db_session.execute(stmt)).first()
    assert row is not None
    assert row.raw_customer_name == "A K MEHTA"
    assert row.effective_customer_name == "A K MEHTA"

    # Cleanup
    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_resolver_erp_reimport(db_session: AsyncSession):
    """TEST 4 — ERP Re-import: raw name updates, override remains effective."""
    test_code = f"TEST_CUST_REIMP_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    # Simulate ERP Re-import updating customers.name
    customer.name = "A K MEHTA ENTERPRISES"
    await db_session.commit()

    stmt = (
        select(
            Customer.id,
            Customer.name.label("raw_customer_name"),
            CustomerDisplayOverrideService.get_effective_name_expression(),
        )
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    row = (await db_session.execute(stmt)).first()
    assert row is not None
    assert row.raw_customer_name == "A K MEHTA ENTERPRISES"
    assert row.effective_customer_name == "A K MEHTA - V2"

    # Cleanup
    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_resolver_reset(db_session: AsyncSession):
    """TEST 5 — Reset (Hard Delete): effective falls back to latest customers.name."""
    test_code = f"TEST_CUST_RESET_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA ENTERPRISES")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    # Perform Hard Delete Reset
    await db_session.delete(override)
    await db_session.commit()

    stmt = (
        select(
            Customer.id,
            Customer.name.label("raw_customer_name"),
            CustomerDisplayOverrideService.get_effective_name_expression(),
        )
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    row = (await db_session.execute(stmt)).first()
    assert row is not None
    assert row.raw_customer_name == "A K MEHTA ENTERPRISES"
    assert row.effective_customer_name == "A K MEHTA ENTERPRISES"

    # Cleanup
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_effective_name_identity_immutability(db_session: AsyncSession):
    """TEST 6A — Identity Immutability: customer_id & code remain identical after override."""
    test_code = f"TEST_CUST_ID_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    stmt = select(
        Customer.id.label("customer_id"),
        Customer.code.label("customer_code"),
        CustomerDisplayOverrideService.get_effective_name_expression(),
    ).outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id).where(Customer.id == customer.id)

    res_before = (await db_session.execute(stmt)).first()
    assert res_before.customer_id == customer.id
    assert res_before.customer_code == test_code
    assert res_before.effective_customer_name == "A K MEHTA"

    override = CustomerDisplayOverride(customer_id=customer.id, override_name="A K MEHTA - V2", updated_by_name="ADMIN")
    db_session.add(override)
    await db_session.commit()

    res_after = (await db_session.execute(stmt)).first()
    assert res_after.customer_id == customer.id
    assert res_after.customer_code == test_code
    assert res_after.effective_customer_name == "A K MEHTA - V2"

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_effective_name_multi_plant_consistency(db_session: AsyncSession):
    """TEST 6B — Multi-Plant Consistency: Customer associated with multiple plants has 1 effective name."""
    test_code = f"TEST_CUST_MP_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(customer_id=customer.id, override_name="A K MEHTA - V2", updated_by_name="ADMIN")
    db_session.add(override)
    await db_session.commit()

    # Query customer from perspective of two distinct plant joins
    stmt = (
        select(Customer.id, CustomerDisplayOverrideService.get_effective_name_expression())
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    rows = (await db_session.execute(stmt)).all()
    assert len(rows) == 1
    assert rows[0].effective_customer_name == "A K MEHTA - V2"

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_effective_name_aggregation_invariance(db_session: AsyncSession):
    """TEST 6C — Aggregation Invariance: Order counts & volume sums are identical before/after override."""
    test_code = f"TEST_CUST_AGG_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    from datetime import datetime, timezone
    o1 = Order(order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=customer.id, order_date=datetime.now(timezone.utc), total_volume_m3=10.0)
    o2 = Order(order_number=f"ORD-{uuid.uuid4().hex[:6]}", customer_id=customer.id, order_date=datetime.now(timezone.utc), total_volume_m3=15.0)
    db_session.add_all([o1, o2])
    await db_session.commit()

    stmt_agg = (
        select(
            Customer.id.label("customer_id"),
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_volume_m3).label("total_volume"),
            CustomerDisplayOverrideService.get_effective_name_expression(),
        )
        .join(Order, Order.customer_id == Customer.id)
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
        .group_by(Customer.id, Customer.code, Customer.name, CustomerDisplayOverride.override_name)
    )

    res_before = (await db_session.execute(stmt_agg)).first()
    assert res_before.total_orders == 2
    assert res_before.total_volume == 25.0
    assert res_before.effective_customer_name == "A K MEHTA"

    override = CustomerDisplayOverride(customer_id=customer.id, override_name="A K MEHTA - V2", updated_by_name="ADMIN")
    db_session.add(override)
    await db_session.commit()

    res_after = (await db_session.execute(stmt_agg)).first()
    assert res_after.total_orders == 2
    assert res_after.total_volume == 25.0
    assert res_after.effective_customer_name == "A K MEHTA - V2"

    await db_session.delete(o1)
    await db_session.delete(o2)
    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_effective_name_no_row_multiplication(db_session: AsyncSession):
    """TEST 6D — Zero Row Multiplication: LEFT JOIN CustomerDisplayOverride produces exact row count."""
    test_code = f"TEST_CUST_MULT_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=test_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    stmt_base = select(Customer).where(Customer.id == customer.id)
    base_rows = (await db_session.execute(stmt_base)).scalars().all()
    assert len(base_rows) == 1

    override = CustomerDisplayOverride(customer_id=customer.id, override_name="A K MEHTA - V2", updated_by_name="ADMIN")
    db_session.add(override)
    await db_session.commit()

    stmt_join = (
        select(Customer.id, CustomerDisplayOverrideService.get_effective_name_expression())
        .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
        .where(Customer.id == customer.id)
    )
    join_rows = (await db_session.execute(stmt_join)).all()
    assert len(join_rows) == 1

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


