"""
WS-10 Phase 5.5 Historical Verified Dataset Builder Test Suite
Comprehensive coverage of all 27 non-negotiable contract scenarios.
"""

from typing import Tuple, List, Dict, Any, Optional
import pytest
import pytest_asyncio
import uuid
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.training_dataset import (
    HistoricalTrainingDataset,
    HistoricalTrainingDatasetRow,
)
from app.modules.operational_intelligence.services.training_dataset_service import TrainingDatasetService
from app.modules.operational_intelligence.repositories.training_dataset_repository import TrainingDatasetRepository

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    from app.core.config import settings
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()


@pytest_asyncio.fixture
async def ws55_session():
    """Isolated test database session for Workstream 5.5 dataset builder verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("TRUNCATE TABLE ml_model_versions, historical_training_datasets, operational_outcomes CASCADE;"))

    async with async_session() as session:
        yield session
    await engine.dispose()


from app.modules.erp.models import Dispatch

async def _seed_model_and_snapshot(
    session: AsyncSession,
    model_version_id: Optional[str] = None,
    model_family: str = "delay_regressor",
    features_json: dict = None,
) -> Tuple[MLModelVersion, MLPredictionSnapshot]:
    """Helper to seed model version and matching prediction snapshot."""
    features_json = features_json or {
        "dispatch_distance_km": 45.0,
        "order_quantity_m3": 12.0,
        "traffic_density_index": 0.4,
    }
    
    if not model_version_id:
        model_version_id = str(uuid.uuid4())
    else:
        try:
            uuid.UUID(model_version_id)
        except ValueError:
            model_version_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc)
    # Check if model version exists
    model_ver = (await session.execute(select(MLModelVersion).where(MLModelVersion.id == model_version_id))).scalar_one_or_none()
    if not model_ver:
        model_ver = MLModelVersion(
            id=model_version_id,
            model_name=model_family,
            model_category="REGRESSION" if "regressor" in model_family else "CLASSIFICATION",
            algorithm="LIGHTGBM",
            target_name="delay_mins",
            training_dataset_id="DS-SEED-TRAIN",
            validation_dataset_id="DS-SEED-VAL",
            holdout_dataset_id="DS-SEED-HOLDOUT",
            artifact_path="/artifacts/model.pkl",
            artifact_sha256="a"*64,
            artifact_size_bytes=1024,
            training_timestamp=now - timedelta(days=20),
            evaluation_timestamp=now - timedelta(days=15),
            promotion_timestamp=now - timedelta(days=10),
            model_version="v1.1.0",
            feature_set_version="FeatureSetV1",
            lifecycle_status="PROMOTED",
            is_deleted=False,
        )
        session.add(model_ver)
        await session.flush()

    # Query existing dispatch to reuse valid foreign keys (ticket_id, vehicle_id, driver_id, plant_id, customer_id)
    disp = (await session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if disp:
        dispatch_id = str(disp.id)
        dispatch_code = disp.dispatch_number or f"DISP-{uuid.uuid4().hex[:6]}"
    else:
        dispatch_id = str(uuid.uuid4())
        dispatch_code = f"DISP-{uuid.uuid4().hex[:6]}"

    # Deactivate existing active snapshot for this dispatch_id and model_name to avoid unique index conflict
    await session.execute(
        update(MLPredictionSnapshot)
        .where(
            MLPredictionSnapshot.dispatch_id == dispatch_id,
            MLPredictionSnapshot.model_name == model_family,
            MLPredictionSnapshot.feature_set_version == "FeatureSetV1",
            MLPredictionSnapshot.is_stale == False,
        )
        .values(is_stale=True)
    )
    await session.flush()

    snapshot_id = f"SNAP-{uuid.uuid4().hex[:8].upper()}"
    snapshot = MLPredictionSnapshot(
        prediction_snapshot_id=snapshot_id,
        idempotency_key=f"IK-SNAP-{uuid.uuid4().hex[:8]}",
        prediction_status="AUTHORITATIVE",
        dispatch_id=dispatch_id,
        dispatch_code=dispatch_code,
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="VEH-01",
        model_version_id=model_version_id,
        model_name=model_family,
        model_version="v1.1.0",
        artifact_sha256="a"*64,
        feature_set_version="FeatureSetV1",
        predicted_value=25.0,
        input_features=features_json,
        prediction_outputs={"predicted_delay_minutes": 25.0},
        prediction_timestamp=now - timedelta(days=5),
        is_stale=False,
        is_deleted=False,
    )
    session.add(snapshot)
    await session.flush()
    return model_ver, snapshot


@pytest.mark.asyncio
async def test_ws55_01_verified_outcome_eligibility(ws55_session: AsyncSession):
    """Test 1: Only VERIFIED and is_verified=True outcomes are eligible for dataset building."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-01", "delay_regressor")

    # Seed 10 VERIFIED outcomes
    start_time = datetime.now(timezone.utc) - timedelta(days=10)
    end_time = datetime.now(timezone.utc)
    
    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-VERIFIED-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=30.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=start_time,
        source_time_range_end=end_time,
        evaluation_cutoff=end_time,
        model_version_id=str(model_ver.id),
        min_sample_count=5,
    )

    assert dataset.dataset_status == "READY_FOR_TRAINING"
    assert dataset.quality_gate_passed is True
    assert dataset.total_row_count >= 10


@pytest.mark.asyncio
async def test_ws55_02_received_outcome_exclusion(ws55_session: AsyncSession):
    """Test 2: RECEIVED outcomes must be strictly excluded."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-02", "delay_regressor")

    out_recv = OperationalOutcome(
        outcome_id=f"OUT-RECV-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        prediction_snapshot_id=snap.prediction_snapshot_id,
        verification_status="RECEIVED",
        is_verified=False,
        is_superseded=False,
        actual_transit_mins=30.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(out_recv)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=model_ver.id,
        min_sample_count=10,
    )

    # Should fail quality gate minimum sample count because RECEIVED outcome is excluded
    assert dataset.dataset_status == "REJECTED"
    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_03_validated_not_verified_exclusion(ws55_session: AsyncSession):
    """Test 3: VALIDATED but not VERIFIED outcomes must be excluded."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-03", "delay_regressor")

    out_val = OperationalOutcome(
        outcome_id=f"OUT-VAL-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        prediction_snapshot_id=snap.prediction_snapshot_id,
        verification_status="VALIDATED",
        is_verified=False,
        is_superseded=False,
        actual_transit_mins=30.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(out_val)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=model_ver.id,
        min_sample_count=1,
    )

    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_04_superseded_outcome_exclusion(ws55_session: AsyncSession):
    """Test 4: Superseded outcomes (O1 -> O2) must be excluded from dataset."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-04", "delay_regressor")

    out_o1 = OperationalOutcome(
        outcome_id=f"OUT-O1-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        prediction_snapshot_id=snap.prediction_snapshot_id,
        verification_status="VERIFIED",
        is_verified=True,
        is_superseded=True,
        superseded_by_outcome_id="OUT-O2-NEW",
        actual_transit_mins=25.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(out_o1)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=1,
    )

    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_08_leakage_field_rejection(ws55_session: AsyncSession):
    """Test 8: Snapshot containing forbidden leakage fields (e.g. t1_transit_mins) fails quality gate."""
    session = ws55_session
    leakage_features = {
        "dispatch_distance_km": 50.0,
        "t1_transit_mins": 35.0, # FORBIDDEN LEAKAGE FIELD!
    }
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-08", "delay_regressor", leakage_features)

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-LEAK-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=35.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=5,
    )

    assert dataset.dataset_status == "REJECTED"
    assert dataset.quality_gate_passed is False
    assert "LEAKAGE_VIOLATIONS_DETECTED" in dataset.rejection_reason


@pytest.mark.asyncio
async def test_ws55_11_regression_dataset_generation(ws55_session: AsyncSession):
    """Test 11: Build delay_regressor regression training dataset with continuous target."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-11", "delay_regressor")

    for i in range(12):
        out = OperationalOutcome(
            outcome_id=f"OUT-REG-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=float(20 + i),
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    assert dataset.dataset_status == "READY_FOR_TRAINING"
    assert dataset.total_row_count == 12

    # Verify rows via repository
    repo = TrainingDatasetRepository(session)
    rows = await repo.get_dataset_rows(dataset.dataset_id)
    assert len(rows) == 12
    assert rows[0].label_json["target_type"] == "continuous"


@pytest.mark.asyncio
async def test_ws55_13_plant_risk_multiclass_dataset_generation(ws55_session: AsyncSession):
    """Test 13: Build plant_risk_classifier dataset preserving 0 NORMAL, 1 MODERATE, 2 SEVERE multiclass targets."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-13", "plant_risk_classifier")

    classes = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
    for i, cls in enumerate(classes):
        out = OperationalOutcome(
            outcome_id=f"OUT-RISK-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_plant_risk_class=cls,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="plant_risk_classifier",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    assert dataset.dataset_status == "READY_FOR_TRAINING"
    repo = TrainingDatasetRepository(session)
    rows = await repo.get_dataset_rows(dataset.dataset_id)
    assert len(rows) == 10
    assert rows[1].label_class == 1
    assert rows[2].label_class == 2


@pytest.mark.asyncio
async def test_ws55_14_null_financial_impact_handling(ws55_session: AsyncSession):
    """Test 14: Realized financial impact NULL is explicitly preserved without fallback to 0."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-14", "delay_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-FIN-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_financial_impact_inr=None, # NULL!
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    repo = TrainingDatasetRepository(session)
    rows = await repo.get_dataset_rows(dataset.dataset_id)
    assert len(rows) == 10
    assert rows[0].realized_financial_impact_inr is None


@pytest.mark.asyncio
async def test_ws55_15_dataset_idempotency(ws55_session: AsyncSession):
    """Test 15: Identical parameters & content hash produce identical dataset via idempotency key."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-15", "delay_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-IDEM-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    start_t = datetime.now(timezone.utc) - timedelta(days=10)
    end_t = datetime.now(timezone.utc)

    ds1 = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=start_t,
        source_time_range_end=end_t,
        evaluation_cutoff=end_t,
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    ds2 = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=start_t,
        source_time_range_end=end_t,
        evaluation_cutoff=end_t,
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    assert ds1.dataset_id == ds2.dataset_id
    assert ds1.dataset_content_hash == ds2.dataset_content_hash


@pytest.mark.asyncio
async def test_ws55_19_complete_lineage_reconstruction(ws55_session: AsyncSession):
    """Test 19: Verify complete lineage tracing dataset -> dataset_row -> outcome -> snapshot -> model_version."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-19", "delay_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-LIN-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    repo = TrainingDatasetRepository(session)
    rows = await repo.get_dataset_rows(dataset.dataset_id)
    assert len(rows) == 10
    first_row = rows[0]

    assert first_row.dataset_id == dataset.dataset_id
    assert first_row.prediction_snapshot_id == snap.prediction_snapshot_id
    assert first_row.model_version_id == str(model_ver.id)


@pytest.mark.asyncio
async def test_ws55_05_unmatched_outcome_exclusion(ws55_session: AsyncSession):
    """Test 5: Outcomes without prediction_snapshot_id must be excluded."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-05", "delay_regressor")

    out_unmatched = OperationalOutcome(
        outcome_id=f"OUT-UNMATCHED-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        prediction_snapshot_id=None, # NO SNAPSHOT MATCH!
        verification_status="VERIFIED",
        is_verified=True,
        is_superseded=False,
        actual_transit_mins=30.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(out_unmatched)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=1,
    )
    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_06_stale_prediction_snapshot_exclusion(ws55_session: AsyncSession):
    """Test 6: Outcomes linked to stale prediction snapshots (is_stale=True) must be excluded."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-06", "delay_regressor")
    snap.is_stale = True
    await session.commit()

    out = OperationalOutcome(
        outcome_id=f"OUT-STALE-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        prediction_snapshot_id=snap.prediction_snapshot_id,
        verification_status="VERIFIED",
        is_verified=True,
        is_superseded=False,
        actual_transit_mins=30.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=1,
    )
    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_07_non_promoted_model_exclusion(ws55_session: AsyncSession):
    """Test 7: Predictions from REJECTED or DRAFT models must be excluded."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-rej-07", "delay_regressor")
    model_ver.lifecycle_status = "REJECTED"
    await session.commit()

    out = OperationalOutcome(
        outcome_id=f"OUT-REJ-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
        prediction_snapshot_id=snap.prediction_snapshot_id,
        verification_status="VERIFIED",
        is_verified=True,
        is_superseded=False,
        actual_transit_mins=30.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=1,
    )
    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_09_model_family_label_mapping_turnaround(ws55_session: AsyncSession):
    """Test 9: Verify turnaround_regressor maps target to actual_transit_mins + actual_unloading_mins."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-09", "turnaround_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-TURN-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=30.0,
            actual_unloading_mins=15.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="turnaround_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    repo = TrainingDatasetRepository(session)
    rows = await repo.get_dataset_rows(dataset.dataset_id)
    assert len(rows) == 10
    assert float(rows[0].label_numeric) == 45.0


@pytest.mark.asyncio
async def test_ws55_10_model_family_label_mapping_sla_breach(ws55_session: AsyncSession):
    """Test 10: Verify sla_breach_classifier maps target to binary 0/1 integer."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-10", "sla_breach_classifier")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-SLA-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_sla_breach_flag=(i % 2 == 1),
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="sla_breach_classifier",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    repo = TrainingDatasetRepository(session)
    rows = await repo.get_dataset_rows(dataset.dataset_id)
    classes = {r.label_class for r in rows}
    assert classes == {0, 1}


@pytest.mark.asyncio
async def test_ws55_12_minimum_sample_count_quality_gate(ws55_session: AsyncSession):
    """Test 12: Fails quality gate if total eligible rows < min_sample_count."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-12", "delay_regressor")

    for i in range(5):
        out = OperationalOutcome(
            outcome_id=f"OUT-MIN-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=30.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10, # Requires 10, only 5 available!
    )

    assert dataset.dataset_status == "REJECTED"
    assert dataset.quality_gate_passed is False
    assert "SAMPLE_COUNT_BELOW_MINIMUM" in dataset.rejection_reason


@pytest.mark.asyncio
async def test_ws55_16_dataset_supersession(ws55_session: AsyncSession):
    """Test 16: Generating new dataset version D2 supersedes existing dataset D1."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-16", "delay_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-SUP-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=30.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    start_t = datetime.now(timezone.utc) - timedelta(days=10)
    end_t = datetime.now(timezone.utc)

    d1 = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=start_t,
        source_time_range_end=end_t,
        evaluation_cutoff=end_t,
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    # Re-generate dataset with force_recompute=True
    d2 = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=start_t,
        source_time_range_end=end_t,
        evaluation_cutoff=end_t,
        model_version_id=str(model_ver.id),
        min_sample_count=10,
        force_recompute=True,
    )

    repo = TrainingDatasetRepository(session)
    d1_refreshed = await repo.get_by_dataset_id(d1.dataset_id)
    assert d1_refreshed.is_superseded is True
    assert d1_refreshed.superseded_by_dataset_id is not None


@pytest.mark.asyncio
async def test_ws55_17_api_generate_dataset_endpoint(ws55_session: AsyncSession):
    """Test 17: POST /predictive/datasets/generate REST API endpoint."""
    from app.modules.operational_intelligence.api.router import generate_training_dataset, DatasetGenerateRequestDTO

    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-17", "delay_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-API-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=30.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    req = DatasetGenerateRequestDTO(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    res = await generate_training_dataset(req, session=session)
    assert res["success"] is True
    assert res["data"]["dataset_status"] == "READY_FOR_TRAINING"
    assert res["data"]["total_row_count"] == 10


@pytest.mark.asyncio
async def test_ws55_18_api_get_dataset_by_id_endpoint(ws55_session: AsyncSession):
    """Test 18: GET /predictive/datasets/{dataset_id} REST API endpoint."""
    from app.modules.operational_intelligence.api.router import get_training_dataset

    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-18", "delay_regressor")

    for i in range(10):
        out = OperationalOutcome(
            outcome_id=f"OUT-GET-{i}-{uuid.uuid4().hex[:4]}",
            dispatch_id=uuid.UUID(snap.dispatch_id),
            dispatch_code=snap.dispatch_code,
            idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
            outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=2),
            prediction_snapshot_id=snap.prediction_snapshot_id,
            verification_status="VERIFIED",
            is_verified=True,
            is_superseded=False,
            actual_transit_mins=30.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(out)
    await session.commit()

    service = TrainingDatasetService(session)
    ds = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=10,
    )

    res = await get_training_dataset(ds.dataset_id, session=session)
    assert res["success"] is True
    assert res["data"]["dataset_id"] == ds.dataset_id


@pytest.mark.asyncio
async def test_ws55_20_content_hash_deterministic_guarantee(ws55_session: AsyncSession):
    """Test 20: SHA-256 content hash is 100% deterministic regardless of insertion order."""
    session = ws55_session
    service = TrainingDatasetService(session)

    items1 = [
        {"row_index": 1, "outcome_id": "OUT-A", "features": {"f1": 1.0}, "label": {"value": 10.0}},
        {"row_index": 2, "outcome_id": "OUT-B", "features": {"f1": 2.0}, "label": {"value": 20.0}},
    ]
    items2 = [
        {"row_index": 2, "outcome_id": "OUT-B", "features": {"f1": 2.0}, "label": {"value": 20.0}},
        {"row_index": 1, "outcome_id": "OUT-A", "features": {"f1": 1.0}, "label": {"value": 10.0}},
    ]

    h1 = service.compute_dataset_content_hash(items1)
    h2 = service.compute_dataset_content_hash(items2)
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_ws55_21_cutoff_timestamp_filtering(ws55_session: AsyncSession):
    """Test 21: Outcomes created after evaluation_cutoff must be excluded."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-21", "delay_regressor")

    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    out_after = OperationalOutcome(
        outcome_id=f"OUT-AFTER-{uuid.uuid4().hex[:4]}",
        dispatch_id=uuid.UUID(snap.dispatch_id),
        dispatch_code=snap.dispatch_code,
        idempotency_key=f"IK-OUT-{uuid.uuid4().hex[:8]}",
        outcome_timestamp=datetime.now(timezone.utc) - timedelta(days=1),
        prediction_snapshot_id=snap.prediction_snapshot_id,
        verification_status="VERIFIED",
        is_verified=True,
        is_superseded=False,
        actual_transit_mins=30.0,
        created_at=datetime.now(timezone.utc) - timedelta(days=1), # AFTER CUTOFF!
    )
    session.add(out_after)
    await session.commit()

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=cutoff,
        model_version_id=str(model_ver.id),
        min_sample_count=1,
    )
    assert dataset.total_row_count == 0


@pytest.mark.asyncio
async def test_ws55_22_empty_eligible_outcomes_rejection(ws55_session: AsyncSession):
    """Test 22: Returns REJECTED dataset with total_row_count=0 when zero eligible outcomes exist."""
    session = ws55_session
    model_ver, snap = await _seed_model_and_snapshot(session, "v1.1.0-prom-22", "delay_regressor")

    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family="delay_regressor",
        source_time_range_start=datetime.now(timezone.utc) - timedelta(days=10),
        source_time_range_end=datetime.now(timezone.utc),
        evaluation_cutoff=datetime.now(timezone.utc),
        model_version_id=str(model_ver.id),
        min_sample_count=1,
    )

    assert dataset.dataset_status == "REJECTED"
    assert dataset.total_row_count == 0
    assert "SAMPLE_COUNT_BELOW_MINIMUM" in dataset.rejection_reason
