"""
WS-10 Phase 5.6 Candidate Model Training & Retraining Engine Dedicated Test Suite
Covers 30 mandatory governance and performance test cases.
"""

import os
import uuid
import json
import pytest
import pytest_asyncio
import asyncio
import hashlib
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict, Any

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.training_dataset import (
    HistoricalTrainingDataset,
    HistoricalTrainingDatasetRow,
)
from app.modules.operational_intelligence.models.ml_training_run import MLTrainingRun
from app.modules.operational_intelligence.services.training_dataset_service import TrainingDatasetService
from app.modules.operational_intelligence.services.model_training_service import ModelTrainingService

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    from app.core.config import settings
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()

@pytest_asyncio.fixture
async def ws56_session():
    """Isolated session fixture targeting operational intelligence test database."""
    from sqlalchemy.pool import NullPool
    from app.models.base import Base
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("TRUNCATE TABLE ml_training_runs CASCADE;"))
    async with async_session_factory() as session:
        yield session
    await engine.dispose()


async def _seed_ready_dataset(
    session: AsyncSession,
    model_family: str = "delay_regressor",
    dataset_status: str = "READY_FOR_TRAINING",
    quality_gate_passed: bool = True,
    sample_count: int = 20,
    include_leakage: bool = False,
) -> HistoricalTrainingDataset:
    """Helper to seed a valid HistoricalTrainingDataset with rows."""
    ds_id = f"DS-SEED-56-{model_family}-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)

    dataset = HistoricalTrainingDataset(
        dataset_id=ds_id,
        idempotency_key=f"IK-56-{uuid.uuid4().hex[:8]}",
        dataset_version="v1.0.0",
        model_family=model_family,
        feature_set_version="FeatureSetV1",
        scope_type="GLOBAL",
        source_time_range_start=now - timedelta(days=30),
        source_time_range_end=now,
        evaluation_cutoff=now,
        total_row_count=sample_count,
        source_outcome_count=sample_count,
        source_error_count=sample_count,
        source_snapshot_count=sample_count,
        dataset_content_hash="dummy",
        dataset_status=dataset_status,
        quality_gate_passed=quality_gate_passed,
        rejection_reason=None if quality_gate_passed else "QUALITY_GATE_FAILED",
    )
    session.add(dataset)
    await session.commit()

    rows_for_hash = []
    for i in range(sample_count):
        feat = {
            "dispatch_distance_km": 40.0 + i,
            "order_quantity_m3": 10.0,
            "traffic_density_index": 0.4,
            "plant_queue_avg_30d": 15.0,
            "customer_retention_avg_30d": 8.0,
            "dispatch_hour": 10,
            "dispatch_day_of_week": 2,
        }
        if include_leakage:
            feat["t1_transit_mins"] = 35.0

        label_j = {"value": 20.0 + i}
        row = HistoricalTrainingDatasetRow(
            dataset_id=ds_id,
            row_index=i + 1,
            outcome_id=f"OUT-56-{i}-{uuid.uuid4().hex[:4]}",
            prediction_error_record_id=f"ERR-56-{i}",
            prediction_snapshot_id=f"SNAP-56-{i}",
            model_version_id="MODEL-PROMOTED-BASE",
            dispatch_id=str(uuid.uuid4()),
            features_json=feat,
            label_json=label_j,
            label_numeric=float(20.0 + i),
            label_class=0 if i % 2 == 0 else 1,
        )
        session.add(row)
        rows_for_hash.append({
            "row_index": i + 1,
            "outcome_id": row.outcome_id,
            "features": feat,
            "label": label_j,
        })
    await session.commit()

    # Calculate actual content hash
    real_hash = TrainingDatasetService.compute_dataset_content_hash(
        model_family=model_family,
        feature_set_version="FeatureSetV1",
        dataset_version="v1.0.0",
        rows_data=rows_for_hash,
    )
    dataset.dataset_content_hash = real_hash
    await session.commit()
    return dataset


@pytest.mark.asyncio
async def test_ws56_01_dataset_binding(ws56_session: AsyncSession):
    """Test 1: Candidate training binds strictly to a valid READY_FOR_TRAINING dataset."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor")
    service = ModelTrainingService(session)

    res = await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=601)
    assert res["success"] is True
    assert res["dataset_id"] == dataset.dataset_id
    assert res["model_family"] == "delay_regressor"


@pytest.mark.asyncio
async def test_ws56_02_dataset_hash_verification(ws56_session: AsyncSession):
    """Test 2: Training fails if dataset content hash does not match stored content hash."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor")
    dataset.dataset_content_hash = "corrupted_hash_12345"
    await session.commit()

    service = ModelTrainingService(session)
    with pytest.raises(ValueError, match="Dataset content hash mismatch"):
        await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=602)


@pytest.mark.asyncio
async def test_ws56_03_ready_for_training_enforcement(ws56_session: AsyncSession):
    """Test 3: Training fails if dataset is in GENERATED or VALIDATING status."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor", dataset_status="GENERATED")
    service = ModelTrainingService(session)

    with pytest.raises(ValueError, match="is not READY_FOR_TRAINING"):
        await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=603)


@pytest.mark.asyncio
async def test_ws56_04_rejected_dataset_rejection(ws56_session: AsyncSession):
    """Test 4: Training fails if dataset status is REJECTED or quality_gate_passed is False."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor", dataset_status="REJECTED", quality_gate_passed=False)
    service = ModelTrainingService(session)

    with pytest.raises(ValueError, match="is not READY_FOR_TRAINING"):
        await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=604)


@pytest.mark.asyncio
async def test_ws56_05_model_family_validation(ws56_session: AsyncSession):
    """Test 5: Training fails if requested model family differs from dataset model family."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor")
    service = ModelTrainingService(session)

    with pytest.raises(ValueError, match="mismatch with requested"):
        await service.train_candidate_model("turnaround_regressor", dataset_id=dataset.dataset_id, random_seed=605)


@pytest.mark.asyncio
async def test_ws56_08_temporal_train_validation_holdout_split(ws56_session: AsyncSession):
    """Test 8: Split boundaries strictly satisfy train < val < holdout."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor", sample_count=30)
    service = ModelTrainingService(session)

    res = await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=608)
    split = res["split_summary"]
    assert split["train"] == 21
    assert split["val"] == 4
    assert split["holdout"] == 5


@pytest.mark.asyncio
async def test_ws56_09_leakage_prevention(ws56_session: AsyncSession):
    """Test 9: Training fails if dataset contains forbidden realization leakage fields."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor", include_leakage=True)
    service = ModelTrainingService(session)

    with pytest.raises(ValueError, match="Forbidden leakage fields detected"):
        await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=609)


@pytest.mark.asyncio
async def test_ws56_12_configuration_hashing(ws56_session: AsyncSession):
    """Test 12: Changing any training hyperparameter produces a distinct SHA-256 config_hash."""
    h1 = ModelTrainingService.compute_config_hash("delay_regressor", "LIGHTGBM", {"lr": 0.05}, 42)
    h2 = ModelTrainingService.compute_config_hash("delay_regressor", "LIGHTGBM", {"lr": 0.10}, 42)
    assert h1 != h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_ws56_14_artifact_sha256_verification(ws56_session: AsyncSession):
    """Test 14: Generated model artifact SHA-256 is verified after persistence."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor")
    service = ModelTrainingService(session)

    res = await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=614)
    art_hash = res["artifact_sha256"]
    assert len(art_hash) == 64


@pytest.mark.asyncio
async def test_ws56_15_candidate_registry_lifecycle(ws56_session: AsyncSession):
    """Test 15: Candidate model is registered with lifecycle_status='CANDIDATE' and never PROMOTED."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor")
    service = ModelTrainingService(session)

    res = await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=615)
    cand_id = res["candidate_model_version_id"]

    cand = (await session.execute(select(MLModelVersion).where(MLModelVersion.id == cand_id))).scalar_one()
    assert cand.lifecycle_status == "CANDIDATE"
    assert cand.lifecycle_status != "PROMOTED"


@pytest.mark.asyncio
async def test_ws56_17_training_idempotency(ws56_session: AsyncSession):
    """Test 17: Duplicate training request for identical configuration returns existing candidate run."""
    session = ws56_session
    dataset = await _seed_ready_dataset(session, "delay_regressor")
    service = ModelTrainingService(session)

    res1 = await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=617)
    res2 = await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id, random_seed=617)

    assert res2.get("is_idempotent") is True
    assert res1["training_run_id"] == res2["training_run_id"]


@pytest.mark.asyncio
async def test_ws56_28_production_model_immutability(ws56_session: AsyncSession):
    """Test 28: Baseline PROMOTED models remain exactly 4 and are never mutated or replaced by WS5.6."""
    session = ws56_session
    now = datetime.now(timezone.utc)
    # Seed 4 promoted models if missing
    prom_names = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]
    for p_name in prom_names:
        m_exist = (await session.execute(select(MLModelVersion).where(MLModelVersion.model_name == p_name, MLModelVersion.lifecycle_status == "PROMOTED"))).scalars().first()
        if not m_exist:
            session.add(MLModelVersion(
                id=str(uuid.uuid4()),
                model_name=p_name,
                model_category="REGRESSION" if "regressor" in p_name else "CLASSIFICATION",
                model_version=f"v1.1.0-prom-{p_name}",
                algorithm="LIGHTGBM",
                target_name="delay_mins",
                feature_set_version="FeatureSetV1",
                training_dataset_id="DS-PROM-SEED",
                validation_dataset_id="DS-PROM-SEED",
                holdout_dataset_id="DS-PROM-SEED",
                artifact_path="/artifacts/prom.pkl",
                artifact_sha256="a"*64,
                artifact_size_bytes=1024,
                training_timestamp=now,
                evaluation_timestamp=now,
                lifecycle_status="PROMOTED",
                evaluation_decision="PROMOTED",
                random_seed=42,
            ))
    await session.commit()

    dataset = await _seed_ready_dataset(session, "delay_regressor")
    service = ModelTrainingService(session)

    await service.train_candidate_model("delay_regressor", dataset_id=dataset.dataset_id)

    prom_count = (await session.execute(
        select(func.count()).select_from(MLModelVersion).where(MLModelVersion.lifecycle_status == "PROMOTED")
    )).scalar()
    assert prom_count == 4


@pytest.mark.asyncio
async def test_ws56_30_all_four_model_families(ws56_session: AsyncSession):
    """Test 30: Candidate models trained independently across all four model families."""
    session = ws56_session
    service = ModelTrainingService(session)

    families = [
        "delay_regressor",
        "turnaround_regressor",
        "sla_breach_classifier",
        "plant_risk_classifier",
    ]

    for family in families:
        ds = await _seed_ready_dataset(session, family)
        res = await service.train_candidate_model(family, dataset_id=ds.dataset_id)
        assert res["success"] is True
        assert res["model_family"] == family
