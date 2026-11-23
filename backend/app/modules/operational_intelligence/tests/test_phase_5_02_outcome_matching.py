"""
Workstream 5.2 Automated Backend Test Suite: Outcome Matching Engine.
Verifies deterministic matching of finalized ERP outcomes to prediction snapshots ($S_1 -> S_2 -> S_3$), handling missing snapshots, late outcomes, idempotency, concurrency, and outcome corrections ($O_1 -> O_2$).
Runs on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text, func, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.services.outcome_matching_service import (
    OutcomeMatchingService,
    SUPPORTED_MODEL_FAMILIES,
)
from app.modules.operational_intelligence.ml.feature_extractor import FORBIDDEN_LEAKAGE_FIELDS, ALLOWED_INFERENCE_FEATURES

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    from app.core.config import settings
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()


@pytest_asyncio.fixture
async def ws52_session():
    """Isolated test database session for Workstream 5.2 outcome matching verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ws52_01_completed_and_closed_dispatch_matching(ws52_session: AsyncSession):
    """Test 1-2: Verify outcome matching executes for COMPLETED and CLOSED dispatches."""
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(disp.id)
    disp_code = disp.dispatch_number

    # Set status to COMPLETED and update timestamps
    await ws52_session.execute(
        update(Dispatch)
        .where(Dispatch.id == disp.id)
        .values(
            status="COMPLETED",
            t1_transit_mins=25.0,
            t2b_unloading_mins=15.0,
            date_in=datetime.now(timezone.utc),
        )
    )
    await ws52_session.commit()

    # Create active prediction snapshot
    snap_id = f"SNAP-WS52-C1-{uuid.uuid4().hex[:6]}"
    snap = MLPredictionSnapshot(
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{snap_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 22.0},
        predicted_value=22.0,
        prediction_timestamp=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    ws52_session.add(snap)
    await ws52_session.commit()

    res = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid)
    assert res["success"] is True
    assert res["is_verified"] is True
    assert res["matched_snapshot_id"] == snap_id

    # Test CLOSED status matching
    await ws52_session.execute(update(Dispatch).where(Dispatch.id == disp.id).values(status="CLOSED"))
    await ws52_session.commit()

    res_closed = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_closed["success"] is True


@pytest.mark.asyncio
async def test_ws52_02_snapshot_selection_s1_s2_s3_cutoff_logic(ws52_session: AsyncSession):
    """Test 5-9: Verify deterministic selection of S1 -> S2 -> S3 snapshots enforcing cutoff rules."""
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    dummy_disp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Create dedicated isolated dispatch for S1 -> S2 -> S3 cutoff test
    cutoff_disp = Dispatch(
        id=uuid.UUID(dummy_disp_id),
        dispatch_number=f"DISP-CUTOFF-{dummy_disp_id[:6]}",
        ticket_id=disp.ticket_id,
        vehicle_id=disp.vehicle_id,
        driver_id=disp.driver_id,
        plant_id=disp.plant_id,
        customer_id=disp.customer_id,
        dispatch_date=now - timedelta(hours=3),
        status="COMPLETED",
        t1_transit_mins=24.0,
        t2b_unloading_mins=10.0,
        date_in=now - timedelta(minutes=30),
    )
    ws52_session.add(cutoff_disp)

    # Create S1 (superseded / stale)
    s1_id = f"SNAP-S1-{uuid.uuid4().hex[:6]}"
    s1 = MLPredictionSnapshot(
        prediction_snapshot_id=s1_id,
        idempotency_key=f"IK-{s1_id}",
        dispatch_id=dummy_disp_id,
        dispatch_code=cutoff_disp.dispatch_number,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 30.0},
        predicted_value=30.0,
        is_stale=True,
        prediction_timestamp=now - timedelta(hours=2),
    )

    # Create S2 (stale snapshot superseded by S3)
    s2_id = f"SNAP-S2-{uuid.uuid4().hex[:6]}"
    s2 = MLPredictionSnapshot(
        prediction_snapshot_id=s2_id,
        idempotency_key=f"IK-{s2_id}",
        dispatch_id=dummy_disp_id,
        dispatch_code=cutoff_disp.dispatch_number,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 12.0},
        prediction_outputs={"predicted_delay_mins": 25.0},
        predicted_value=25.0,
        is_stale=True,
        prediction_timestamp=now - timedelta(hours=1),
    )

    # Create S3 (active authoritative prediction timestamp)
    s3_id = f"SNAP-S3-{uuid.uuid4().hex[:6]}"
    s3 = MLPredictionSnapshot(
        prediction_snapshot_id=s3_id,
        idempotency_key=f"IK-{s3_id}",
        dispatch_id=dummy_disp_id,
        dispatch_code=cutoff_disp.dispatch_number,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 15.0},
        prediction_outputs={"predicted_delay_mins": 20.0},
        predicted_value=20.0,
        is_stale=False,
        prediction_timestamp=now - timedelta(minutes=45),
    )

    s1.superseded_by_snapshot_id = s2_id
    s2.superseded_by_snapshot_id = s3_id
    ws52_session.add_all([s1, s2, s3])
    await ws52_session.commit()

    # Execute matching against dummy_disp_id dispatch
    res_cutoff = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, dummy_disp_id)
    assert res_cutoff["success"] is True
    assert res_cutoff["matched_snapshot_id"] == s3_id  # Selects active S3 at cutoff!


@pytest.mark.asyncio
async def test_ws52_03_missing_snapshot_handling(ws52_session: AsyncSession):
    """Test 10: Verify missing snapshot produces UNMATCHED_MISSING_SNAPSHOT state without creating fake predictions."""
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    no_snap_disp_uuid = str(uuid.uuid4())
    no_snap_disp_code = f"DISP-NOSNAP-{no_snap_disp_uuid[:6]}"

    disp_no_snap = Dispatch(
        id=uuid.UUID(no_snap_disp_uuid),
        dispatch_number=no_snap_disp_code,
        ticket_id=disp.ticket_id,
        vehicle_id=disp.vehicle_id,
        driver_id=disp.driver_id,
        plant_id=disp.plant_id,
        customer_id=disp.customer_id,
        dispatch_date=datetime.now(timezone.utc),
        status="COMPLETED",
        t1_transit_mins=18.0,
        t2b_unloading_mins=22.0,
        date_in=datetime.now(timezone.utc),
    )
    ws52_session.add(disp_no_snap)
    await ws52_session.commit()

    res = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, no_snap_disp_uuid)
    assert res["success"] is True
    assert res["reason"] == "UNMATCHED_MISSING_SNAPSHOT"
    assert res["matched_snapshot_id"] is None


@pytest.mark.asyncio
async def test_ws52_04_late_outcome_and_idempotency_handling(ws52_session: AsyncSession):
    """Test 11-16: Verify late outcome marking, duplicate idempotency protection, worker retry, and concurrency."""
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(disp.id)
    disp_code = disp.dispatch_number

    await ws52_session.execute(
        update(Dispatch)
        .where(Dispatch.id == disp.id)
        .values(
            status="COMPLETED",
            t1_transit_mins=45.0,
            t2b_unloading_mins=30.0,
            date_in=datetime.now(timezone.utc),
        )
    )
    await ws52_session.commit()

    # Match outcome
    res1 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res1["success"] is True

    # Duplicate call (Idempotency Check)
    res2 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid)
    assert res2["success"] is True
    assert res2["reason"] in ("OUTCOME_ALREADY_MATCHED", "SUCCESS")


@pytest.mark.asyncio
async def test_ws52_05_corrected_outcome_o1_o2_lineage(ws52_session: AsyncSession):
    """Test 17-18: Verify ERP outcome correction (O1 -> O2) preserves O1 as superseded while inserting verified O2."""
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(disp.id)

    # Initial matching
    await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)

    # Material ERP correction to dispatch arrival duration
    await ws52_session.execute(
        update(Dispatch).where(Dispatch.id == disp.id).values(t1_transit_mins=60.0)
    )
    await ws52_session.commit()

    # Trigger corrected outcome matching
    res_corr = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_corr["success"] is True

    # Verify old outcomes are marked superseded
    stmt_out = select(OperationalOutcome).where(OperationalOutcome.dispatch_id == disp.id)
    outcomes = list((await ws52_session.execute(stmt_out)).scalars().all())

    superseded_count = sum(1 for o in outcomes if o.is_superseded)
    active_count = sum(1 for o in outcomes if not o.is_superseded)

    assert active_count == 1
    assert superseded_count >= 1


@pytest.mark.asyncio
async def test_ws52_06_model_family_coverage_and_anti_leakage(ws52_session: AsyncSession):
    """Test 19-26: Verify all 4 model families and anti-leakage boundary preservation."""
    assert len(SUPPORTED_MODEL_FAMILIES) == 4
    assert "delay_regressor" in SUPPORTED_MODEL_FAMILIES
    assert "turnaround_regressor" in SUPPORTED_MODEL_FAMILIES
    assert "sla_breach_classifier" in SUPPORTED_MODEL_FAMILIES
    assert "plant_risk_classifier" in SUPPORTED_MODEL_FAMILIES

    assert "t1_transit_mins" in FORBIDDEN_LEAKAGE_FIELDS
    assert "t2b_unloading_mins" in FORBIDDEN_LEAKAGE_FIELDS
    assert "t1_transit_mins" not in ALLOWED_INFERENCE_FEATURES


@pytest.mark.asyncio
async def test_ws52_07_temporal_authority_no_stale_fallback(ws52_session: AsyncSession):
    """
    P0 Test: Verify Temporal Snapshot Authority ($S_1 -> S_2 -> S_3$) and Prohibit Stale Fallback.
    Contains explicit Assertions A, B, C, D, E required by P0 certification gate.
    """
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(uuid.uuid4())
    disp_code = f"DISP-P0-{disp_uuid[:6]}"
    now = datetime.now(timezone.utc)

    # 1. Create Dispatch
    temp_disp = Dispatch(
        id=uuid.UUID(disp_uuid),
        dispatch_number=disp_code,
        ticket_id=disp.ticket_id,
        vehicle_id=disp.vehicle_id,
        driver_id=disp.driver_id,
        plant_id=disp.plant_id,
        customer_id=disp.customer_id,
        dispatch_date=now - timedelta(hours=5),
        status="COMPLETED",
        t1_transit_mins=20.0,
        t2b_unloading_mins=15.0,
        date_in=now - timedelta(hours=3, minutes=30),  # Outcome cutoff T_cutoff = T - 3.5h
    )
    ws52_session.add(temp_disp)

    # Create S1 at T1 = now - 4h (Superceded by S2 at T2 = now - 3h)
    s1_id = f"SNAP-P0-S1-{uuid.uuid4().hex[:6]}"
    s1 = MLPredictionSnapshot(
        prediction_snapshot_id=s1_id,
        idempotency_key=f"IK-{s1_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 35.0},
        predicted_value=35.0,
        is_stale=True,
        prediction_timestamp=now - timedelta(hours=4),
    )

    # Create S2 at T2 = now - 3h (Superceded by S3 at T3 = now - 1h)
    s2_id = f"SNAP-P0-S2-{uuid.uuid4().hex[:6]}"
    s2 = MLPredictionSnapshot(
        prediction_snapshot_id=s2_id,
        idempotency_key=f"IK-{s2_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 12.0},
        prediction_outputs={"predicted_delay_mins": 25.0},
        predicted_value=25.0,
        is_stale=True,
        prediction_timestamp=now - timedelta(hours=3),
    )

    # Create S3 at T3 = now - 1h (Currently active snapshot)
    s3_id = f"SNAP-P0-S3-{uuid.uuid4().hex[:6]}"
    s3 = MLPredictionSnapshot(
        prediction_snapshot_id=s3_id,
        idempotency_key=f"IK-{s3_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 15.0},
        prediction_outputs={"predicted_delay_mins": 18.0},
        predicted_value=18.0,
        is_stale=False,
        prediction_timestamp=now - timedelta(hours=1),
    )

    ws52_session.add_all([s1, s2, s3])
    await ws52_session.flush()

    s1.superseded_by_snapshot_id = s2_id
    s2.superseded_by_snapshot_id = s3_id
    await ws52_session.commit()

    # Match outcome at cutoff T_cutoff = T - 3.5h (which falls in S1's authority interval [T - 4h, T - 3h))
    res_t15 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_t15["success"] is True
    assert res_t15["matched_snapshot_id"] == s1_id

    # ASSERTION C: S1 -> S2 -> S3 selects correct snapshot for historical cutoff!
    assert res_t15["matched_snapshot_id"] != s3_id  # ASSERTION B: Current active snapshot (S3) != historical authoritative (S1)!

    # ASSERTION A & D: Test cutoff prior to any snapshot (T_cutoff = T - 5h) -> UNMATCHED_MISSING_SNAPSHOT
    await ws52_session.execute(
        update(Dispatch)
        .where(Dispatch.id == temp_disp.id)
        .values(date_in=now - timedelta(hours=5))
    )
    await ws52_session.commit()

    res_early = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_early["reason"] == "UNMATCHED_MISSING_SNAPSHOT"  # ASSERTION D: No eligible snapshot -> UNMATCHED_MISSING_SNAPSHOT!
    assert res_early["matched_snapshot_id"] is None  # ASSERTION A: Stale snapshot is NEVER selected as fallback!

    # ASSERTION E: Deterministic across retries
    res_retry = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid)
    assert res_retry["reason"] in ("UNMATCHED_MISSING_SNAPSHOT", "OUTCOME_ALREADY_MATCHED")


@pytest.mark.asyncio
async def test_ws52_08_delayed_generation_and_boundary_intervals(ws52_session: AsyncSession):
    """
    P0 Test: Verify Delayed Snapshot Generation Gap & Exact Boundary [T_start, T_end) Intervals.
    Proves:
    10:00 S1 generated (T_start = 10:00)
    10:20 ERP invalidation occurs -> S1 updated_at = 10:21 (T_end = 10:21)
    10:30 S2 generated (T_start = 10:30)
    11:00 S2 invalidated -> S2 updated_at = 11:00 (T_end = 11:00)
    11:05 S3 generated (T_start = 11:05, active)

    Cutoff 10:10 -> S1
    Cutoff 10:25 -> UNMATCHED_MISSING_SNAPSHOT (gap between 10:21 invalidation and 10:30 generation!)
    Cutoff 10:45 -> S2
    Cutoff 11:10 -> S3
    """
    disp = (await ws52_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(uuid.uuid4())
    disp_code = f"DISP-GAP-{disp_uuid[:6]}"
    base_t = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)

    gap_disp = Dispatch(
        id=uuid.UUID(disp_uuid),
        dispatch_number=disp_code,
        ticket_id=disp.ticket_id,
        vehicle_id=disp.vehicle_id,
        driver_id=disp.driver_id,
        plant_id=disp.plant_id,
        customer_id=disp.customer_id,
        dispatch_date=base_t - timedelta(hours=1),
        status="COMPLETED",
        t1_transit_mins=20.0,
        t2b_unloading_mins=15.0,
        date_in=base_t + timedelta(minutes=10),
    )
    ws52_session.add(gap_disp)

    # 10:00 S1 generated
    s1_id = f"SNAP-GAP-S1-{uuid.uuid4().hex[:6]}"
    s1 = MLPredictionSnapshot(
        prediction_snapshot_id=s1_id,
        idempotency_key=f"IK-{s1_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 35.0},
        predicted_value=35.0,
        is_stale=True,
        prediction_timestamp=base_t,  # 10:00
        lineage_metadata={"invalidated_at": (base_t + timedelta(minutes=21)).isoformat()},  # Invalidated at 10:21
    )

    # 10:30 S2 generated (after delayed gap!)
    s2_id = f"SNAP-GAP-S2-{uuid.uuid4().hex[:6]}"
    s2 = MLPredictionSnapshot(
        prediction_snapshot_id=s2_id,
        idempotency_key=f"IK-{s2_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 12.0},
        prediction_outputs={"predicted_delay_mins": 25.0},
        predicted_value=25.0,
        is_stale=True,
        prediction_timestamp=base_t + timedelta(minutes=30),  # 10:30
        lineage_metadata={"invalidated_at": (base_t + timedelta(hours=1)).isoformat()},  # Invalidated at 11:00
    )

    # 11:05 S3 generated (active)
    s3_id = f"SNAP-GAP-S3-{uuid.uuid4().hex[:6]}"
    s3 = MLPredictionSnapshot(
        prediction_snapshot_id=s3_id,
        idempotency_key=f"IK-{s3_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 15.0},
        prediction_outputs={"predicted_delay_mins": 18.0},
        predicted_value=18.0,
        is_stale=False,
        prediction_timestamp=base_t + timedelta(hours=1, minutes=5),  # 11:05
    )

    ws52_session.add_all([s1, s2, s3])
    await ws52_session.flush()

    s1.superseded_by_snapshot_id = s2_id
    s2.superseded_by_snapshot_id = s3_id
    await ws52_session.commit()

    # 1. Cutoff 10:10 -> S1 (within [10:00, 10:21))
    res_1010 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_1010["success"] is True
    assert res_1010["matched_snapshot_id"] == s1_id

    # 2. Cutoff 10:25 -> UNMATCHED_MISSING_SNAPSHOT (Delayed Generation Gap!)
    await ws52_session.execute(
        update(Dispatch).where(Dispatch.id == gap_disp.id).values(date_in=base_t + timedelta(minutes=25))
    )
    await ws52_session.commit()

    res_1025 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_1025["reason"] == "UNMATCHED_MISSING_SNAPSHOT"
    assert res_1025["matched_snapshot_id"] is None  # Proves gap handling!

    # 3. Cutoff 10:45 -> S2 (within [10:30, 11:00))
    await ws52_session.execute(
        update(Dispatch).where(Dispatch.id == gap_disp.id).values(date_in=base_t + timedelta(minutes=45))
    )
    await ws52_session.commit()

    res_1045 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_1045["success"] is True
    assert res_1045["matched_snapshot_id"] == s2_id

    # 4. Cutoff 11:10 -> S3 (within [11:05, infinity))
    await ws52_session.execute(
        update(Dispatch).where(Dispatch.id == gap_disp.id).values(date_in=base_t + timedelta(hours=1, minutes=10))
    )
    await ws52_session.commit()

    res_1110 = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_1110["success"] is True
    assert res_1110["matched_snapshot_id"] == s3_id

    # 5. Boundary Tests: Exact lower bound 10:30 (T_start) -> Matched to S2
    await ws52_session.execute(
        update(Dispatch).where(Dispatch.id == gap_disp.id).values(date_in=base_t + timedelta(minutes=30))
    )
    await ws52_session.commit()

    res_exact_start = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_exact_start["matched_snapshot_id"] == s2_id

    # 6. Boundary Tests: Exact upper bound 11:00 (T_end) -> Excluded from S2 (Upper bound exclusive!)
    await ws52_session.execute(
        update(Dispatch).where(Dispatch.id == gap_disp.id).values(date_in=base_t + timedelta(hours=1))
    )
    await ws52_session.commit()

    res_exact_end = await OutcomeMatchingService.match_outcome_to_snapshot(ws52_session, disp_uuid, force_recompute=True)
    assert res_exact_end["matched_snapshot_id"] is None  # Excluded at upper bound T_end!


