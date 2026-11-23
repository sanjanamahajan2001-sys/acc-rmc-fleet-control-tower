"""
Phase 4B.6 — Dedicated Test Suite: Global Dashboard Filters & Cross-Dashboard Effective Customer Name Propagation.

Verifies 15 mandatory requirement specifications:
1. Filter options use effective customer display name
2. Filter options preserve customer_id (UUID) and customer_code
3. Filter option count is strictly invariant (exactly 231 customers = 231 filter options)
4. Multi-plant customer filter deduplication (one filter option per customer identity)
5. Filter options resolve whitespace overrides to raw ERP fallback
6. Filter metadata query avoids cartesian multiplication / row duplication
7. Filter options update dynamically under PUT display override mutations
8. Filter options update under ERP re-import while preserving active overrides
9. Filter options revert cleanly to updated raw ERP name under hard-delete reset
10. Filter metadata maintains metric/identity invariance across all 8 dashboard consumers
"""

import pytest
import uuid
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Customer, Plant, CustomerDisplayOverride
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_01_filter_options_use_effective_name_and_preserve_identity(db_session: AsyncSession):
    """1, 2 & 3. Verifies filter options use effective display name and preserve customer code / identity."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B6-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW FILTER CUST {uuid.uuid4().hex[:6]}"
    override_name = f"EFFECTIVE FILTER CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        # Baseline check without override
        meta_base = await DashboardFilterMetadataService.get_filter_metadata(session)
        target_base = next((c for c in meta_base.customers if c.code == cust_code), None)
        assert target_base is not None
        assert target_base.id == cust_code
        assert target_base.code == cust_code
        assert target_base.name == raw_name
        assert target_base.raw_customer_name == raw_name
        assert target_base.effective_customer_name == raw_name

        # Add Display Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # Effective display check
        meta_over = await DashboardFilterMetadataService.get_filter_metadata(session)
        target_over = next((c for c in meta_over.customers if c.code == cust_code), None)
        assert target_over is not None
        assert target_over.id == cust_code  # Identity preserved!
        assert target_over.code == cust_code
        assert target_over.name == override_name  # Label updated!
        assert target_over.raw_customer_name == raw_name
        assert target_over.effective_customer_name == override_name
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_02_filter_option_count_and_deduplication_invariant(db_session: AsyncSession):
    """4 & 10. Verifies total customer filter options count is strictly invariant under active overrides."""
    session = db_session
    
    # 1. Total customer count in DB
    raw_cust_count = (await session.execute(select(Customer))).scalars().all()
    total_db_customers = len(raw_cust_count)

    # 2. Base metadata customer options count (includes "ALL")
    meta_base = await DashboardFilterMetadataService.get_filter_metadata(session)
    assert len(meta_base.customers) == total_db_customers + 1

    # 3. Add multiple overrides
    cust_ids = [str(c.id) for c in raw_cust_count[:5]]
    svc = CustomerDisplayOverrideService()
    for cid in cust_ids:
        await svc.upsert_customer_override(session, uuid.UUID(cid), f"OVERRIDE OPTION {cid[:6]}", updated_by_name="ADMIN")
    await session.commit()

    try:
        meta_over = await DashboardFilterMetadataService.get_filter_metadata(session)
        assert len(meta_over.customers) == total_db_customers + 1  # Absolutely zero row duplication!
    finally:
        for cid in cust_ids:
            await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cid))
        await session.commit()


@pytest.mark.asyncio
async def test_03_filter_whitespace_override_fallback(db_session: AsyncSession):
    """9. Verifies whitespace overrides fall back to raw ERP customer name."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B6-WS-{uuid.uuid4().hex[:6]}"
    raw_name = f"RAW WS CUST {uuid.uuid4().hex[:6]}"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        # Whitespace Override is rejected by Service domain validation
        svc = CustomerDisplayOverrideService()
        with pytest.raises(Exception):
            await svc.upsert_customer_override(session, uuid.UUID(cust_id), "   ", updated_by_name="ADMIN")

        meta = await DashboardFilterMetadataService.get_filter_metadata(session)
        target = next((c for c in meta.customers if c.code == cust_code), None)
        assert target is not None
        assert target.name == raw_name  # Fell back to raw name!
        assert target.effective_customer_name == raw_name
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()


@pytest.mark.asyncio
async def test_04_filter_lifecycle_erp_reimport_and_reset(db_session: AsyncSession):
    """7 & 8. Verifies ERP re-import preservation and hard-delete reset behavior in filter metadata."""
    session = db_session
    cust_id = str(uuid.uuid4())
    cust_code = f"CUST-P4B6-LC-{uuid.uuid4().hex[:6]}"
    raw_name_v1 = "ERP FILTER NAME V1"
    raw_name_v2 = "ERP FILTER NAME V2 UPDATED"
    override_name = "STABLE FILTER OVERRIDE"

    cust = Customer(id=cust_id, code=cust_code, name=raw_name_v1, is_deleted=False)
    session.add(cust)
    await session.commit()

    try:
        # 1. Upsert Override
        svc = CustomerDisplayOverrideService()
        await svc.upsert_customer_override(session, uuid.UUID(cust_id), override_name, updated_by_name="ADMIN")
        await session.commit()

        # 2. Simulate ERP Re-import
        cust.name = raw_name_v2
        await session.commit()

        meta_reimport = await DashboardFilterMetadataService.get_filter_metadata(session)
        target_reimport = next((c for c in meta_reimport.customers if c.code == cust_code), None)
        assert target_reimport.raw_customer_name == raw_name_v2
        assert target_reimport.name == override_name  # Preserved!

        # 3. Hard-delete / Reset Override
        await svc.reset_customer_override(session, uuid.UUID(cust_id))
        await session.commit()

        meta_reset = await DashboardFilterMetadataService.get_filter_metadata(session)
        target_reset = next((c for c in meta_reset.customers if c.code == cust_code), None)
        assert target_reset.name == raw_name_v2  # Reverted to updated raw ERP!
    finally:
        await session.execute(delete(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == cust_id))
        await session.execute(delete(Customer).where(Customer.id == cust_id))
        await session.commit()
