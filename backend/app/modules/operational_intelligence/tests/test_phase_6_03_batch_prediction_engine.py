"""
WS-10 Phase 6.3 Watermarked Batch Prediction Engine Test Suite
Validates persistent cursor high-watermarks, lexicographical (created_at, dispatch_id) tie-breaking,
failure atomicity, mid-batch failure recovery, crash idempotency, and empty-batch boundary handling.
"""

import os
import uuid
import pytest
import pytest_asyncio
import hashlib
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Dispatch, Ticket, Order, Customer, Plant, Vehicle, Driver
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.services.authoritative_resolver import AuthoritativeModelResolver
from app.modules.operational_intelligence.services.batch_prediction_engine import BatchPredictionEngine
from app.modules.operational_intelligence.services.production_inference_service import ProductionInferenceService

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()

@pytest_asyncio.fixture
async def ws63_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ml_batch_processing_cursors (
                id UUID PRIMARY KEY,
                batch_job_name VARCHAR(100) NOT NULL UNIQUE,
                last_processed_timestamp TIMESTAMPTZ,
                last_processed_dispatch_id VARCHAR(100),
                total_dispatches_processed BIGINT NOT NULL DEFAULT 0,
                total_snapshots_generated BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                is_deleted BOOLEAN NOT NULL DEFAULT false,
                deleted_at TIMESTAMPTZ,
                version INT NOT NULL DEFAULT 1
            );
        """))
        await conn.execute(text("ALTER TABLE ml_batch_processing_cursors ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;"))
        await conn.execute(text("DELETE FROM ml_batch_processing_cursors;"))
        await conn.execute(text("DELETE FROM dispatches WHERE dispatch_number LIKE 'DISP-%';"))

    async with async_session_factory() as session:
        await session.rollback()
        yield session

    await engine.dispose()


async def _seed_all_promoted_models(session: AsyncSession):
    now = datetime.now(timezone.utc)
    families = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]

    for fam in families:
        uid = uuid.uuid4().hex[:6]
        sha = hashlib.sha256(f"art-{fam}-{uid}".encode()).hexdigest()
        model = MLModelVersion(
            id=str(uuid.uuid4()),
            model_name=fam,
            model_category="REGRESSION" if "regressor" in fam else "CLASSIFICATION",
            algorithm="LIGHTGBM",
            target_name="target",
            training_dataset_id=f"DS-{uid}",
            artifact_path=f"/tmp/virtual_art_{fam}_{uid}.pkl",
            artifact_sha256=sha,
            artifact_size_bytes=2048,
            training_timestamp=now,
            model_version=f"v1.1.0-prom-{uid}",
            feature_set_version="FeatureSetV1",
            lifecycle_status="PROMOTED",
            is_deleted=False,
        )
        session.add(model)

    await session.commit()

    # Fast-forward batch cursor past all baseline historical dispatches
    max_ts_res = await session.execute(text("SELECT max(created_at), max(id::text) FROM dispatches;"))
    row = max_ts_res.first()
    max_ts, max_id = row[0] if row else None, row[1] if row else None

    engine = BatchPredictionEngine(session)
    cursor = await engine.get_or_create_cursor()
    cursor.last_processed_timestamp = max_ts
    cursor.last_processed_dispatch_id = max_id
    session.add(cursor)
    await session.commit()


@pytest.mark.asyncio
async def test_ws63_01_watermark_cursor_initialization(ws63_session: AsyncSession):
    """Test 1: Initializes high-watermark cursor entity on first run."""
    session = ws63_session
    engine = BatchPredictionEngine(session)

    cursor = await engine.get_or_create_cursor()
    assert cursor.batch_job_name == BatchPredictionEngine.CURSOR_JOB_NAME
    assert cursor.last_processed_timestamp is None
    assert cursor.total_dispatches_processed == 0


@pytest.mark.asyncio
async def test_ws63_02_same_timestamp_ordering_and_tie_breaking(ws63_session: AsyncSession):
    """Test 2: Processes dispatches with identical created_at timestamps across small batches without skipping."""
    session = ws63_session
    await _seed_all_promoted_models(session)

    res_max = await session.execute(text("SELECT COALESCE(max(created_at), now()) FROM dispatches;"))
    base_time = res_max.scalar()
    fixed_time = (base_time + timedelta(hours=1)).replace(microsecond=0)

    uids = sorted([uuid.uuid4() for _ in range(5)])

    p = Plant(id=uuid.uuid4(), name="ACC VASCO", code=f"PLANT-{uuid.uuid4().hex[:6]}")
    session.add(p)
    v = Vehicle(id=uuid.uuid4(), code=f"VEH-{uuid.uuid4().hex[:6]}", license_plate="GA01V1234")
    session.add(v)
    drv = Driver(id=uuid.uuid4(), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name="John Doe")
    session.add(drv)

    for u in uids:
        c = Customer(id=uuid.uuid4(), name=f"CUST-{u.hex[:4]}", code=f"CUST-{u.hex[:4]}")
        session.add(c)
        o = Order(id=uuid.uuid4(), customer_id=c.id, order_number=f"ORD-{u.hex[:4]}", order_date=fixed_time)
        session.add(o)
        t = Ticket(id=uuid.uuid4(), order_id=o.id, plant_id=p.id, ticket_number=f"TICK-{u.hex[:4]}", ticket_date=fixed_time, delivered_volume_m3=6.0)
        session.add(t)
        d = Dispatch(
            id=u,
            ticket_id=t.id,
            vehicle_id=v.id,
            driver_id=drv.id,
            plant_id=p.id,
            customer_id=c.id,
            dispatch_number=f"DISP-SAME-{u.hex[:4]}",
            dispatch_date=fixed_time,
            created_at=fixed_time,
        )
        session.add(d)
    await session.commit()

    engine = BatchPredictionEngine(session)
    cursor = await engine.get_or_create_cursor()
    cursor.last_processed_timestamp = fixed_time - timedelta(seconds=10)
    cursor.last_processed_dispatch_id = None
    session.add(cursor)
    await session.commit()
    
    # Process batch 1 with size 2
    res1 = await engine.process_incremental_batch(max_dispatches=2)
    assert res1.dispatches_processed == 2
    cursor1 = await engine.get_or_create_cursor()
    assert cursor1.last_processed_timestamp == fixed_time
    assert cursor1.last_processed_dispatch_id == str(uids[1])

    # Process batch 2 with size 3
    res2 = await engine.process_incremental_batch(max_dispatches=5)
    assert res2.dispatches_processed == 3
    cursor2 = await engine.get_or_create_cursor()
    assert cursor2.last_processed_dispatch_id == str(uids[4])


@pytest.mark.asyncio
async def test_ws63_03_boundary_dispatch_predicate(ws63_session: AsyncSession):
    """Test 3: Verifies lexicographical predicate excludes dispatch_id <= watermark and includes dispatch_id > watermark."""
    session = ws63_session
    await _seed_all_promoted_models(session)

    res_max = await session.execute(text("SELECT COALESCE(max(created_at), now()) FROM dispatches;"))
    base_time = res_max.scalar()
    fixed_time = (base_time + timedelta(hours=1)).replace(microsecond=0)

    u1, u2, u3 = sorted([uuid.uuid4() for _ in range(3)])

    p = Plant(id=uuid.uuid4(), name="ACC VASCO", code=f"PLANT-{uuid.uuid4().hex[:6]}")
    session.add(p)
    v = Vehicle(id=uuid.uuid4(), code=f"VEH-{uuid.uuid4().hex[:6]}", license_plate="GA01V1234")
    session.add(v)
    drv = Driver(id=uuid.uuid4(), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name="John Doe")
    session.add(drv)

    for u in [u1, u2, u3]:
        c = Customer(id=uuid.uuid4(), name=f"CUST-{u.hex[:4]}", code=f"CUST-{u.hex[:4]}")
        session.add(c)
        o = Order(id=uuid.uuid4(), customer_id=c.id, order_number=f"ORD-{u.hex[:4]}", order_date=fixed_time)
        session.add(o)
        t = Ticket(id=uuid.uuid4(), order_id=o.id, plant_id=p.id, ticket_number=f"TICK-{u.hex[:4]}", ticket_date=fixed_time, delivered_volume_m3=6.0)
        session.add(t)
        d = Dispatch(id=u, ticket_id=t.id, vehicle_id=v.id, driver_id=drv.id, plant_id=p.id, customer_id=c.id, dispatch_number=f"DISP-BOUND-{u.hex[:4]}", dispatch_date=fixed_time, created_at=fixed_time)
        session.add(d)
    await session.commit()

    engine = BatchPredictionEngine(session)
    cursor = await engine.get_or_create_cursor()
    cursor.last_processed_timestamp = fixed_time
    cursor.last_processed_dispatch_id = str(u1)
    session.add(cursor)
    await session.commit()

    # Next batch must pick u2 and u3, skipping u1
    res = await engine.process_incremental_batch(max_dispatches=10)
    assert res.dispatches_processed == 2
    assert res.watermark_dispatch_id == str(u3)


@pytest.mark.asyncio
async def test_ws63_04_mid_batch_failure_recovery(ws63_session: AsyncSession):
    """Test 4: Injects failure at 2nd dispatch. Verifies watermark advances ONLY up to 1st dispatch and leaves 2nd eligible."""
    session = ws63_session
    await _seed_all_promoted_models(session)

    res_max = await session.execute(text("SELECT COALESCE(max(created_at), now()) FROM dispatches;"))
    base_time = res_max.scalar()
    fixed_time = (base_time + timedelta(hours=1)).replace(microsecond=0)

    u1, u2 = sorted([uuid.uuid4() for _ in range(2)])

    p = Plant(id=uuid.uuid4(), name="ACC VASCO", code=f"PLANT-{uuid.uuid4().hex[:6]}")
    session.add(p)
    v = Vehicle(id=uuid.uuid4(), code=f"VEH-{uuid.uuid4().hex[:6]}", license_plate="GA01V1234")
    session.add(v)
    drv = Driver(id=uuid.uuid4(), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name="John Doe")
    session.add(drv)

    for u in [u1, u2]:
        c = Customer(id=uuid.uuid4(), name=f"CUST-{u.hex[:4]}", code=f"CUST-{u.hex[:4]}")
        session.add(c)
        o = Order(id=uuid.uuid4(), customer_id=c.id, order_number=f"ORD-{u.hex[:4]}", order_date=fixed_time)
        session.add(o)
        t = Ticket(id=uuid.uuid4(), order_id=o.id, plant_id=p.id, ticket_number=f"TICK-{u.hex[:4]}", ticket_date=fixed_time, delivered_volume_m3=6.0)
        session.add(t)
        d = Dispatch(id=u, ticket_id=t.id, vehicle_id=v.id, driver_id=drv.id, plant_id=p.id, customer_id=c.id, dispatch_number=f"DISP-FAIL-{u.hex[:4]}", dispatch_date=fixed_time, created_at=fixed_time)
        session.add(d)
    await session.commit()

    engine = BatchPredictionEngine(session)
    cursor = await engine.get_or_create_cursor()
    cursor.last_processed_timestamp = fixed_time - timedelta(seconds=10)
    cursor.last_processed_dispatch_id = None
    session.add(cursor)
    await session.commit()

    # Patch execute_inference to fail on u2
    original_execute = ProductionInferenceService.execute_inference
    async def mock_execute(self, dispatch_id, model_family=None, force_reprocess=False):
        if str(dispatch_id) == str(u2):
            raise RuntimeError("Simulated mid-batch failure on u2")
        return await original_execute(self, dispatch_id, model_family, force_reprocess)

    with patch.object(ProductionInferenceService, "execute_inference", mock_execute):
        res = await engine.process_incremental_batch(max_dispatches=5)
        assert res.dispatches_processed == 1
        assert res.failed_dispatch_id == str(u2)
        assert res.watermark_dispatch_id == str(u1)

    # Verify second run without patch succeeds on u2
    res2 = await engine.process_incremental_batch(max_dispatches=5)
    assert res2.dispatches_processed == 1
    assert res2.watermark_dispatch_id == str(u2)


@pytest.mark.asyncio
async def test_ws63_05_crash_recovery_idempotency(ws63_session: AsyncSession):
    """Test 5: Process predicts but crashes before watermark commit. Re-run uses WS6.2 snapshot idempotency."""
    session = ws63_session
    await _seed_all_promoted_models(session)

    res_max = await session.execute(text("SELECT COALESCE(max(created_at), now()) FROM dispatches;"))
    base_time = res_max.scalar()
    now = (base_time + timedelta(hours=1)).replace(microsecond=0)

    u1 = uuid.uuid4()
    p = Plant(id=uuid.uuid4(), name="ACC VASCO", code=f"PLANT-{uuid.uuid4().hex[:6]}")
    session.add(p)
    v = Vehicle(id=uuid.uuid4(), code=f"VEH-{uuid.uuid4().hex[:6]}", license_plate="GA01V1234")
    session.add(v)
    drv = Driver(id=uuid.uuid4(), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name="John Doe")
    session.add(drv)
    c = Customer(id=uuid.uuid4(), name="CUST-CRASH-01", code=f"CUST-{uuid.uuid4().hex[:6]}")
    session.add(c)
    o = Order(id=uuid.uuid4(), customer_id=c.id, order_number=f"ORD-{uuid.uuid4().hex[:6]}", order_date=now)
    session.add(o)
    t = Ticket(id=uuid.uuid4(), order_id=o.id, plant_id=p.id, ticket_number=f"TICK-{uuid.uuid4().hex[:6]}", ticket_date=now, delivered_volume_m3=6.0)
    session.add(t)
    d = Dispatch(id=u1, ticket_id=t.id, vehicle_id=v.id, driver_id=drv.id, plant_id=p.id, customer_id=c.id, dispatch_number=f"DISP-{uuid.uuid4().hex[:6]}", dispatch_date=now, created_at=now)
    session.add(d)
    await session.commit()

    # Step 1: Manually execute inference for u1 without updating cursor (simulates crash before cursor commit)
    inf_service = ProductionInferenceService(session)
    res_inf1 = await inf_service.execute_inference(str(u1))
    assert res_inf1.snapshots_created == 4 # 4 model families

    # Step 2: Run BatchPredictionEngine
    engine = BatchPredictionEngine(session)
    cursor = await engine.get_or_create_cursor()
    cursor.last_processed_timestamp = now - timedelta(seconds=10)
    session.add(cursor)
    await session.commit()

    res_batch = await engine.process_incremental_batch(max_dispatches=5)
    assert res_batch.dispatches_processed == 1
    assert res_batch.snapshots_created == 0 # 0 created, reused 4 due to idempotency!
    assert res_batch.snapshots_reused == 4


@pytest.mark.asyncio
async def test_ws63_06_empty_batch_watermark_preservation(ws63_session: AsyncSession):
    """Test 6: Empty batch execution preserves watermark timestamp and ID."""
    session = ws63_session
    engine = BatchPredictionEngine(session)

    res = await engine.process_incremental_batch(max_dispatches=10)
    assert res.dispatches_processed == 0
    assert res.watermark_timestamp is None

    cursor = await engine.get_or_create_cursor()
    assert cursor.total_dispatches_processed == 0


@pytest.mark.asyncio
async def test_ws63_07_subsequent_batch_idempotency_no_op(ws63_session: AsyncSession):
    """Test 7: Subsequent run when all DB dispatches are processed yields 0 processed records."""
    session = ws63_session
    await _seed_all_promoted_models(session)

    engine = BatchPredictionEngine(session)
    res1 = await engine.process_incremental_batch(max_dispatches=5000)

    res2 = await engine.process_incremental_batch(max_dispatches=5000)
    assert res2.dispatches_processed == 0
    assert res2.snapshots_created == 0


@pytest.mark.asyncio
async def test_ws63_08_transaction_rollback_safety(ws63_session: AsyncSession):
    """Test 8: Database transaction rollback leaves cursor intact without corruption."""
    session = ws63_session
    engine = BatchPredictionEngine(session)

    cursor = await engine.get_or_create_cursor()
    initial_processed = cursor.total_dispatches_processed

    # Simulate rollback
    await session.rollback()

    cursor_after = await engine.get_or_create_cursor()
    assert cursor_after.total_dispatches_processed == initial_processed

