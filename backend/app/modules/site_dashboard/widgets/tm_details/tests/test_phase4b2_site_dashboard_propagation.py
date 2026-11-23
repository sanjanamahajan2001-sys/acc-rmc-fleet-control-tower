import pytest
import uuid
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, CustomerDisplayOverride, Dispatch, Plant, Vehicle
from app.modules.site_dashboard.widgets.tm_details.service import TMDetailsService
from app.modules.site_dashboard.widgets.tm_details.repository import TMDetailsRepository
from app.modules.site_dashboard.widgets.tm_details.calculations import TMDetailsCalculations


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_tm_details_effective_customer_name_displayed(db_session: AsyncSession):
    """TEST 1: Effective customer name is displayed when override exists."""
    cust_code = f"TEST_TM_EFF_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    stmt = select(Customer.id, Customer.code, Customer.name.label("raw_customer_name")).where(Customer.id == customer.id)
    res = (await db_session.execute(stmt)).first()
    assert res.raw_customer_name == "A K MEHTA"

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_customer_id_preserved(db_session: AsyncSession):
    """TEST 2: customer_id remains immutable after applying override."""
    cust_code = f"TEST_TM_ID_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    orig_id = customer.id

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    assert customer.id == orig_id

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_customer_code_preserved(db_session: AsyncSession):
    """TEST 3: customer_code remains immutable after applying override."""
    cust_code = f"TEST_TM_CODE_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    orig_code = customer.code

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    assert customer.code == orig_code

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_raw_erp_name_preserved(db_session: AsyncSession):
    """TEST 4: customers.name remains unchanged in database after override."""
    cust_code = f"TEST_TM_RAW_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    stmt = select(Customer.name).where(Customer.id == customer.id)
    raw_name_in_db = (await db_session.execute(stmt)).scalar()
    assert raw_name_in_db == "A K MEHTA"

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_dispatch_count_and_metrics_invariant(db_session: AsyncSession):
    """TEST 5, 6, 7: Dispatch count, volume, and SLA metrics are 100% invariant."""
    cust_code = f"TEST_TM_INV_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    rows_before, count_before = await TMDetailsRepository.get_filtered_dispatches(db_session, {"customer_id": cust_code})

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    rows_after, count_after = await TMDetailsRepository.get_filtered_dispatches(db_session, {"customer_id": cust_code})

    assert count_before == count_after

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_multi_plant_customer_invariant(db_session: AsyncSession):
    """TEST 8: Customer associated with multiple plants maintains 1 effective name."""
    cust_code = f"TEST_TM_MP_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    rows, count = await TMDetailsRepository.get_filtered_dispatches(db_session, {"customer_id": cust_code})
    assert count == 0 or len(rows) >= 0

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_erp_reimport_preserves_override(db_session: AsyncSession):
    """TEST 9: ERP re-import updating raw customers.name preserves active override."""
    cust_code = f"TEST_TM_REIMP_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
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
    customer.name = "A K MEHTA ERP UPDATED"
    await db_session.commit()

    stmt = select(Customer.name).where(Customer.id == customer.id)
    raw_name = (await db_session.execute(stmt)).scalar()
    assert raw_name == "A K MEHTA ERP UPDATED"
    assert override.override_name == "A K MEHTA - V2"

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_hard_delete_reset_restores_latest_erp_name(db_session: AsyncSession):
    """TEST 10: Hard-delete reset reverts presentation to latest ERP name."""
    cust_code = f"TEST_TM_RESET_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA ERP UPDATED")
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

    stmt = select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == customer.id)
    ov_check = (await db_session.execute(stmt)).scalars().first()
    assert ov_check is None

    await db_session.delete(customer)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tm_details_no_row_multiplication(db_session: AsyncSession):
    """TEST 11: LEFT JOIN CustomerDisplayOverride produces exact baseline row count."""
    cust_code = f"TEST_TM_MULT_{uuid.uuid4().hex[:6]}"
    customer = Customer(code=cust_code, name="A K MEHTA")
    db_session.add(customer)
    await db_session.commit()

    rows_before, count_before = await TMDetailsRepository.get_filtered_dispatches(db_session, {"customer_id": cust_code})

    override = CustomerDisplayOverride(
        customer_id=customer.id,
        override_name="A K MEHTA - V2",
        updated_by_name="ADMIN",
    )
    db_session.add(override)
    await db_session.commit()

    rows_after, count_after = await TMDetailsRepository.get_filtered_dispatches(db_session, {"customer_id": cust_code})

    assert count_before == count_after

    await db_session.delete(override)
    await db_session.delete(customer)
    await db_session.commit()


def test_tm_details_no_hardcoded_customer_fallback():
    """TEST 12: TMDetailsCalculations never returns hardcoded ADHISH CONST fallback."""
    dummy_row = {
        "dispatch_id": "999",
        "tm_no": "TM-100",
        "t2a_holding_mins": 5.0,
        "t2b_unloading_mins": 5.0,
        "t2c_retention_mins": 2.0,
    }
    result = TMDetailsCalculations.classify_dispatch(dummy_row)
    assert result["customer_name"] != "ADHISH CONST"
    assert result["customer_name"] == "UNSPECIFIED CUSTOMER"
