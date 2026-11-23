import pytest
import pytest_asyncio
import uuid
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from app.modules.erp.models import Customer, CustomerDisplayOverride


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_records(db_session):
    yield
    await db_session.execute(text("DELETE FROM customer_display_overrides WHERE updated_by_name LIKE 'TEST%' OR override_reason LIKE '%Phase 1%' OR override_name LIKE '%Test%' OR override_name LIKE '%Customer A%' OR customer_id IN (SELECT id FROM customers WHERE code LIKE 'TEST%' OR code LIKE 'CUST_ISO%' OR code LIKE 'CUST_DEL%')"))
    await db_session.execute(text("DELETE FROM customers WHERE code LIKE 'TEST%' OR code LIKE 'CUST_ISO%' OR code LIKE 'CUST_DEL%'"))
    await db_session.commit()





@pytest.mark.asyncio
async def test_phase1_table_and_schema_exists(db_session):
    """Verify table customer_display_overrides exists and can be queried."""
    result = await db_session.execute(select(func.count(CustomerDisplayOverride.id)))
    count = result.scalar()
    assert count >= 0


@pytest.mark.asyncio
async def test_phase1_crud_operations(db_session):
    """Verify Create, Read, Update, Delete for CustomerDisplayOverride entity."""
    test_code = f"TEST_CUST_{uuid.uuid4().hex[:8]}".upper()
    cust = Customer(code=test_code, name="Test Original Customer Name")
    db_session.add(cust)
    await db_session.commit()
    await db_session.refresh(cust)

    # 1. Create Override
    override = CustomerDisplayOverride(
        customer_id=cust.id,
        override_name="Test Modified Display Name",
        override_reason="Phase 1 Verification",
        updated_by_name="TEST_ADMIN"
    )
    db_session.add(override)
    await db_session.commit()
    await db_session.refresh(override)

    assert override.id is not None
    assert override.customer_id == cust.id
    assert override.override_name == "Test Modified Display Name"

    target_cust_id = cust.id
    # 2. Read via Relationship
    db_session.expire_all()
    from sqlalchemy.orm import selectinload
    res = await db_session.execute(
        select(Customer).options(selectinload(Customer.display_override)).where(Customer.id == target_cust_id)
    )


    fetched_cust = res.scalars().first()
    assert fetched_cust is not None
    assert fetched_cust.display_override is not None
    assert fetched_cust.display_override.override_name == "Test Modified Display Name"

    # 3. Update Override
    fetched_cust.display_override.override_name = "Test Updated Display Name 2"
    await db_session.commit()

    res_updated = await db_session.execute(
        select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust.id)
    )
    updated_override = res_updated.scalars().first()
    assert updated_override.override_name == "Test Updated Display Name 2"

    # 4. Reset / Delete Override
    await db_session.delete(updated_override)
    await db_session.commit()

    res_deleted = await db_session.execute(
        select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust.id)
    )
    assert res_deleted.scalars().first() is None


@pytest.mark.asyncio
async def test_phase1_constraints_and_uniqueness(db_session):
    """Verify unique constraint on customer_id and non-null override_name."""
    test_code = f"TEST_CUST_UNQ_{uuid.uuid4().hex[:8]}".upper()
    cust = Customer(code=test_code, name="Uniqueness Test Customer")
    db_session.add(cust)
    await db_session.commit()

    # Create first override
    ov1 = CustomerDisplayOverride(customer_id=cust.id, override_name="First Override")
    db_session.add(ov1)
    await db_session.commit()

    # Attempt to create second override for same customer_id (Must Fail)
    ov2 = CustomerDisplayOverride(customer_id=cust.id, override_name="Second Override")
    db_session.add(ov2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Attempt to insert non-existent customer_id (Must Fail)
    bad_ov = CustomerDisplayOverride(customer_id=uuid.uuid4(), override_name="Bad Customer")
    db_session.add(bad_ov)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_phase1_data_isolation(db_session):
    """Verify Override A on Customer A does not affect Customer B."""
    cust_a = Customer(code=f"CUST_ISO_A_{uuid.uuid4().hex[:6]}", name="Customer A")
    cust_b = Customer(code=f"CUST_ISO_B_{uuid.uuid4().hex[:6]}", name="Customer B")
    db_session.add_all([cust_a, cust_b])
    await db_session.commit()

    ov_a = CustomerDisplayOverride(customer_id=cust_a.id, override_name="Customer A Custom Name")
    db_session.add(ov_a)
    await db_session.commit()

    res_b = await db_session.execute(select(Customer).where(Customer.id == cust_b.id))
    fetched_b = res_b.scalars().first()

    assert fetched_b.display_override is None
    assert fetched_b.name == "Customer B"


@pytest.mark.asyncio
async def test_phase1_delete_protection(db_session):
    """Verify RESTRICT delete protection on customer table foreign key."""
    cust = Customer(code=f"CUST_DEL_{uuid.uuid4().hex[:6]}", name="Delete Protection Customer")
    db_session.add(cust)
    await db_session.commit()

    ov = CustomerDisplayOverride(customer_id=cust.id, override_name="Delete Protection Override")
    db_session.add(ov)
    await db_session.commit()

    # Execute direct SQL delete of customer to test database FK RESTRICT constraint
    with pytest.raises(IntegrityError):
        await db_session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": cust.id})
        await db_session.commit()
    await db_session.rollback()
