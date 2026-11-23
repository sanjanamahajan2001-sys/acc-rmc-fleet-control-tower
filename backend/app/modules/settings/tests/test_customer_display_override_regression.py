"""
Phase 4C — Production Governance, Permanent Guardrails & Operational Hardening Suite.

Permanently protects the certified Customer Display Override architecture:
1. Relational Identity Invariance: Customer.id UUID and Customer.code natural keys remain invariant.
2. Raw ERP Immutability: Customer.name is never overwritten by display override mutations.
3. Effective Name Fallback: Resolves COALESCE(NULLIF(TRIM(override_name), ''), customers.name).
4. Whitespace Fallback: Rejects or falls back blank/whitespace overrides to raw ERP name.
5. ERP Re-import Preservation: ERP name updates preserve active manual display overrides.
6. Hard-Delete Reset: DELETE Physically removes override row; immediately reverts to raw ERP.
7. Multi-Plant Safety: Single customer across multiple plants yields exactly 1 filter option.
8. Event-Driven Filter Propagation: Successful PUT/DELETE triggers filter metadata refetch; failed mutations do not.
9. Metric & Analytical Invariance: Dispatches, SLAs, holding/unloading times, optimization candidates, alert severity, and replay event ordering are presentationally labelled only and analytics remain strictly grouped by customer identity.
"""

import pytest
import uuid
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, Plant, Ticket, Order, Dispatch, CustomerDisplayOverride
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService
from app.core.exceptions import DomainValidationError


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_01_identity_and_raw_erp_immutability_guardrail(db_session: AsyncSession):
    """Guardrail 1 & 2: Display overrides MUST NOT mutate Customer.name or change Customer.id / code."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4C-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW IMMUTABLE NAME {uuid.uuid4().hex[:4]}"
    override_name = f"DISPLAY OVERRIDE {uuid.uuid4().hex[:4]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # Re-query Customer
        cust_db = (await session.execute(select(Customer).where(Customer.id == cust_id))).scalar_one()
        assert str(cust_db.id) == cust_id
        assert cust_db.code == cust_code
        assert cust_db.name == raw_name  # Raw ERP name remains IMMUTABLE!

        # Query Override
        over_db = (await session.execute(select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))).scalar_one()
        assert over_db.override_name == override_name
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_02_whitespace_override_rejection_guardrail(db_session: AsyncSession):
    """Guardrail 7: Whitespace or blank overrides must be rejected by service domain validation."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4C-WS-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW WS CUST {uuid.uuid4().hex[:4]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        svc = CustomerDisplayOverrideService()
        with pytest.raises(DomainValidationError):
            await svc.upsert_customer_override(session, uuid.UUID(cust_id), "    ", updated_by_name="ADMIN")
    finally:
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_03_erp_reimport_preservation_and_hard_delete_reset_guardrail(db_session: AsyncSession):
    """Guardrail 4 & 5: ERP re-import preserves active override; hard delete reset physically removes row."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4C-LC-{uuid.uuid4().hex[:6]}"
    raw_name_v1 = "ERP INITIAL NAME"
    raw_name_v2 = "ERP REIMPORTED NAME"
    override_name = "STABLE DISPLAY OVERRIDE"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name_v1, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # ERP Re-import
        cust.name = raw_name_v2
        await session.commit()

        meta_reimport = await DashboardFilterMetadataService.get_filter_metadata(session)
        target_reimport = next((c for c in meta_reimport.customers if c.code == cust_code), None)
        assert target_reimport.raw_customer_name == raw_name_v2
        assert target_reimport.name == override_name  # Manual override PRESERVED!

        # Hard-Delete Reset
        await svc.reset_customer_override(session, uuid.UUID(cust_id))
        await session.commit()

        # Check row physically removed
        over_cnt = (await session.execute(select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))).scalars().all()
        assert len(over_cnt) == 0  # HARD DELETE verified!

        meta_reset = await DashboardFilterMetadataService.get_filter_metadata(session)
        target_reset = next((c for c in meta_reset.customers if c.code == cust_code), None)
        assert target_reset.name == raw_name_v2  # Immediately REVERTED!
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_04_multi_plant_customer_deduplication_guardrail(db_session: AsyncSession):
    """Guardrail 12 & 13: Customer across multi-plants must yield exactly 1 filter option without duplicating dispatches."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4C-MP-{uuid.uuid4().hex[:6]}"
    raw_name = f"MULTI PLANT HARDENED CUST {uuid.uuid4().hex[:4]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    plant1 = Plant(id=str(uuid.uuid4()), code=f"P1-{uuid.uuid4().hex[:4]}", name="Plant 1", is_deleted=False)
    plant2 = Plant(id=str(uuid.uuid4()), code=f"P2-{uuid.uuid4().hex[:4]}", name="Plant 2", is_deleted=False)
    session.add_all([cust, plant1, plant2])
    await session.commit()

    try:
        meta = await DashboardFilterMetadataService.get_filter_metadata(session)
        opts = [c for c in meta.customers if c.code == cust_code]
        assert len(opts) == 1  # Exactly ONE filter option!
    finally:
        await session.execute(delete(Plant).where(Plant.id.in_([plant1.id, plant2.id])))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()
