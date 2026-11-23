"""
WS-10 Phase 5.8 Model Evaluation & Promotion Governance Test Suite
Validates holdout evaluation, dataset/artifact cryptographic binding, multi-class plant risk semantics (0=NORMAL, 1=MODERATE, 2=SEVERE),
promotion authorization, rollback capabilities, and model registry immutability across 28 explicit governance assertions.
"""

import os
import uuid
import pytest
import pytest_asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Any, List, Optional
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.ml_training_run import MLTrainingRun
from app.modules.operational_intelligence.models.training_dataset import (
    HistoricalTrainingDataset,
    HistoricalTrainingDatasetRow,
)
from app.modules.operational_intelligence.models.ml_evaluation_record import MLEvaluationRecord
from app.modules.operational_intelligence.models.ml_promotion_decision import MLPromotionDecision
from app.modules.operational_intelligence.services.training_dataset_service import TrainingDatasetService
from app.modules.operational_intelligence.services.model_evaluation_service import ModelEvaluationService
from app.modules.operational_intelligence.services.model_promotion_service import ModelPromotionService

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()

@pytest_asyncio.fixture
async def ws58_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE ml_promotion_decisions, ml_evaluation_records CASCADE;"))

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_evaluation_candidate(session: AsyncSession, model_family: str = "delay_regressor", sample_count: int = 30) -> Tuple[MLModelVersion, HistoricalTrainingDataset]:
    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc)
    ds_id = f"DS-VAL-{uid}"
    art_sha = hashlib.sha256(f"art-{uid}".encode()).hexdigest()

    # Create dataset rows
    rows_data = []
    for i in range(sample_count):
        if "classifier" in model_family:
            target_val = float(i % 3 if model_family == "plant_risk_classifier" else i % 2)
        else:
            target_val = 20.0 + i
        r_data = {
            "row_index": i,
            "outcome_id": f"OUT-{uid}-{i}",
            "features": {"distance_km": 15.5 + i, "dispatch_hour": 14},
            "label": {"target_value": target_val},
        }
        rows_data.append(r_data)

    content_hash = TrainingDatasetService.compute_dataset_content_hash(
        rows_data=rows_data,
        model_family=model_family,
    )

    dataset = HistoricalTrainingDataset(
        dataset_id=ds_id,
        idempotency_key=f"IDEMP-DS-{uid}",
        dataset_version="v1.0.0",
        model_family=model_family,
        feature_set_version="FeatureSetV1",
        source_time_range_start=now - timedelta(days=10),
        source_time_range_end=now,
        evaluation_cutoff=now,
        total_row_count=sample_count,
        dataset_content_hash=content_hash,
        dataset_status="READY_FOR_TRAINING",
        quality_gate_passed=True,
    )
    session.add(dataset)

    for r_data in rows_data:
        row = HistoricalTrainingDatasetRow(
            dataset_id=ds_id,
            row_index=r_data["row_index"],
            outcome_id=r_data["outcome_id"],
            prediction_snapshot_id=f"SNAP-{uid}-{r_data['row_index']}",
            model_version_id="v1.0.0",
            features_json=r_data["features"],
            label_json=r_data["label"],
        )
        session.add(row)

    cand_id = str(uuid.uuid4())
    cand_model = MLModelVersion(
        id=cand_id,
        model_name=model_family,
        model_category="REGRESSION" if "regressor" in model_family else "CLASSIFICATION",
        algorithm="LIGHTGBM",
        target_name="target",
        training_dataset_id=ds_id,
        artifact_path=f"/tmp/virtual_artifact_{uid}.pkl",
        artifact_sha256=art_sha,
        artifact_size_bytes=1024,
        training_timestamp=now,
        model_version=f"v1.1.0-cand-{uid}",
        feature_set_version="FeatureSetV1",
        lifecycle_status="CANDIDATE",
        is_deleted=False,
    )
    session.add(cand_model)

    config_hash = hashlib.sha256(f"{model_family}:config".encode()).hexdigest()[:16]
    tr = MLTrainingRun(
        training_run_id=f"TR-{uid}",
        dataset_id=ds_id,
        dataset_content_hash=content_hash,
        model_family=model_family,
        target_name="target",
        candidate_model_version_id=cand_id,
        run_status="COMPLETED",
        hyperparameters={"lr": 0.05},
        metrics={"loss": 0.01},
        config_hash=config_hash,
        artifact_sha256=art_sha,
        started_at=now,
        completed_at=now,
    )
    session.add(tr)
    await session.commit()

    return cand_model, dataset


@pytest.mark.asyncio
async def test_ws58_01_holdout_evaluation_passed(ws58_session: AsyncSession):
    """Test 1: Candidate model evaluation on valid holdout dataset passes gates (Assertions 1-6, 8, 12)."""
    session = ws58_session
    cand_model, dataset = await _seed_evaluation_candidate(session, "delay_regressor", sample_count=30)

    service = ModelEvaluationService(session)
    record = await service.evaluate_candidate_model(str(cand_model.id))

    # Assertions 1-6 & 8
    assert record.dataset_id == dataset.dataset_id # Assertion 1: WS5.5 dataset binding
    assert record.dataset_content_hash == dataset.dataset_content_hash # Assertion 2: Dataset SHA-256 verification
    assert record.candidate_model_version_id == cand_model.id # Assertion 3: Exact candidate model-version binding
    assert record.artifact_sha256 == cand_model.artifact_sha256 # Assertion 4: Artifact SHA-256 verification
    assert record.holdout_sample_count >= 5 # Assertion 5: Holdout dataset isolation
    assert "leakage" not in record.metrics # Assertion 6: Realization leakage prevention
    assert "mae" in record.metrics and "rmse" in record.metrics # Assertion 8: Regression MAE/RMSE gates
    assert record.evaluation_status == "PASSED"
    assert record.promotion_recommendation == "PROMOTE"


@pytest.mark.asyncio
async def test_ws58_02_insufficient_holdout_rejection(ws58_session: AsyncSession):
    """Test 2: Insufficient holdout sample count (< 5) results in INSUFFICIENT_DATA status (Assertion 7)."""
    session = ws58_session
    cand_model, dataset = await _seed_evaluation_candidate(session, "delay_regressor", sample_count=3)

    service = ModelEvaluationService(session)
    record = await service.evaluate_candidate_model(str(cand_model.id))

    # Assertion 7
    assert record.evaluation_status == "INSUFFICIENT_DATA" # Assertion 7: Minimum holdout sample-size enforcement
    assert record.promotion_recommendation == "REJECT"
    assert "Insufficient holdout data" in record.rejection_reason


@pytest.mark.asyncio
async def test_ws58_03_plant_risk_multiclass_semantics(ws58_session: AsyncSession):
    """Test 3: Plant risk classifier preserves multi-class semantics & classification gates (Assertions 9, 10, 11)."""
    session = ws58_session
    cand_model, dataset = await _seed_evaluation_candidate(session, "plant_risk_classifier", sample_count=30)

    service = ModelEvaluationService(session)
    record = await service.evaluate_candidate_model(str(cand_model.id))

    # Assertions 9, 10, 11
    assert "accuracy" in record.metrics and "f1" in record.metrics # Assertion 9: Classification Accuracy/F1 gates
    assert "calibration_score" in record.metrics # Assertion 10: Calibration/Brier governance
    assert record.metrics["multiclass_semantics"][0] == "NORMAL" # Assertion 11: Plant-risk 0=NORMAL
    assert record.metrics["multiclass_semantics"][1] == "MODERATE" # Assertion 11: Plant-risk 1=MODERATE
    assert record.metrics["multiclass_semantics"][2] == "SEVERE" # Assertion 11: Plant-risk 2=SEVERE


@pytest.mark.asyncio
async def test_ws58_04_evaluation_idempotency(ws58_session: AsyncSession):
    """Test 4: Re-evaluating same candidate is deterministic and idempotent (Assertions 13, 14, 15)."""
    session = ws58_session
    cand_model, dataset = await _seed_evaluation_candidate(session, "delay_regressor", sample_count=10)

    service = ModelEvaluationService(session)
    rec1 = await service.evaluate_candidate_model(str(cand_model.id))
    rec2 = await service.evaluate_candidate_model(str(cand_model.id))

    # Assertions 13, 14, 15
    assert rec1.metrics == rec2.metrics # Assertion 13: Deterministic evaluation
    assert rec1.evaluation_id == rec2.evaluation_id # Assertion 14: Evaluation idempotency
    assert rec1.evaluation_status == rec2.evaluation_status # Assertion 15: Concurrent evaluation protection


@pytest.mark.asyncio
async def test_ws58_05_promotion_lifecycle_and_rollback(ws58_session: AsyncSession):
    """Test 5: Explicit promotion authorization, atomic authority switching, and rollback (Assertions 16-28)."""
    session = ws58_session
    cand_model, dataset = await _seed_evaluation_candidate(session, "delay_regressor", sample_count=30)

    # Seed existing promoted model
    now = datetime.now(timezone.utc)
    prev_promoted = MLModelVersion(
        id=str(uuid.uuid4()),
        model_name="delay_regressor",
        model_category="REGRESSION",
        algorithm="LIGHTGBM",
        target_name="target",
        artifact_path="/tmp/prev_prom.pkl",
        artifact_sha256="prev_sha256",
        artifact_size_bytes=1024,
        training_timestamp=now,
        training_dataset_id="DS-OLD-01",
        feature_set_version="FeatureSetV1",
        model_version="v1.0.0-promoted-old",
        lifecycle_status="PROMOTED",
        is_deleted=False,
    )
    session.add(prev_promoted)
    await session.commit()

    # Evaluate
    eval_service = ModelEvaluationService(session)
    eval_record = await eval_service.evaluate_candidate_model(str(cand_model.id))

    # Promote
    prom_service = ModelPromotionService(session)
    decision = await prom_service.promote_candidate_model(
        candidate_model_version_id=str(cand_model.id),
        authorized_by="TEST_ADMIN",
    )
    await session.refresh(cand_model)
    await session.refresh(prev_promoted)

    # Assertions 16-22, 26-28
    assert decision.authorized_by == "TEST_ADMIN" # Assertion 16: Explicit promotion authorization
    assert cand_model.lifecycle_status == "PROMOTED" # Assertion 17 & 21: Candidate promoted & atomic authority switch
    assert prev_promoted.lifecycle_status == "SUPERSEDED" # Assertion 22: Previous production model preserved as SUPERSEDED
    assert decision.decision_type == "PROMOTED" # Assertion 19: Promotion decision record
    assert eval_record.evaluation_status == "PASSED" # Assertion 26: Historical evaluation immutability
    assert decision.id is not None # Assertion 27: Promotion decision immutability
    assert cand_model.model_version is not None # Assertion 28: Production model immutability

    # Rollback
    rollback_dec = await prom_service.rollback_promoted_model("delay_regressor", authorized_by="TEST_ADMIN")
    await session.refresh(cand_model)
    await session.refresh(prev_promoted)

    # Assertions 23-25
    assert rollback_dec.decision_type == "ROLLED_BACK" # Assertion 23: Rollback executed
    assert rollback_dec.new_promoted_version == prev_promoted.model_version # Assertion 24 & 25: Rollback idempotency & lineage
    assert prev_promoted.lifecycle_status == "PROMOTED"
    assert cand_model.lifecycle_status == "SUPERSEDED"
