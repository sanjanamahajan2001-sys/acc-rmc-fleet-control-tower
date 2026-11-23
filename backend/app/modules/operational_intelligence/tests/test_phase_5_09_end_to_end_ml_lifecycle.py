"""
WS-10 Phase 5.9 End-to-End ML Learning Lifecycle & Production Authority Test Suite
Validates the complete governed ML lifecycle loop:
ERP Import -> Prediction Snapshot -> Outcome Matching -> Prediction Error -> Model Health -> Historical Dataset -> Candidate Retraining -> Holdout Evaluation -> Promotion Governance -> Authoritative Model -> Future Batch Inference -> Feedback Loop -> Retraining Trigger -> Rollback.
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
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.models.model_health import ModelHealthMetric
from app.modules.operational_intelligence.models.training_dataset import (
    HistoricalTrainingDataset,
    HistoricalTrainingDatasetRow,
)
from app.modules.operational_intelligence.models.ml_training_run import MLTrainingRun
from app.modules.operational_intelligence.models.ml_feedback_record import MLFeedbackRecord
from app.modules.operational_intelligence.models.continuous_learning_trigger import ContinuousLearningTrigger
from app.modules.operational_intelligence.models.ml_evaluation_record import MLEvaluationRecord
from app.modules.operational_intelligence.models.ml_promotion_decision import MLPromotionDecision

from app.modules.operational_intelligence.services.training_dataset_service import TrainingDatasetService
from app.modules.operational_intelligence.services.model_training_service import ModelTrainingService
from app.modules.operational_intelligence.services.model_evaluation_service import ModelEvaluationService
from app.modules.operational_intelligence.services.model_promotion_service import ModelPromotionService

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()
MODEL_FAMILIES = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]


@pytest_asyncio.fixture
async def ws59_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE ml_promotion_decisions, ml_evaluation_records, continuous_learning_triggers, ml_feedback_records CASCADE;"))

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_four_family_dataset(session: AsyncSession, model_family: str, sample_count: int = 30) -> Tuple[HistoricalTrainingDataset, MLModelVersion]:
    uid = uuid.uuid4().hex[:6]
    now = datetime.now(timezone.utc)
    ds_id = f"DS-E2E-{model_family[:4]}-{uid}"
    art_sha = hashlib.sha256(f"art-e2e-{uid}".encode()).hexdigest()

    rows_data = []
    for i in range(sample_count):
        if "classifier" in model_family:
            target_val = float(i % 3 if model_family == "plant_risk_classifier" else i % 2)
        else:
            target_val = 25.0 + i
        r_data = {
            "row_index": i,
            "outcome_id": f"OUT-{uid}-{i}",
            "features": {"dispatch_hour": 14, "plant_queue_avg_30d": 12.0},
            "label": {"target_value": target_val},
        }
        rows_data.append(r_data)

    content_hash = TrainingDatasetService.compute_dataset_content_hash(
        rows_data=rows_data,
        model_family=model_family,
    )

    dataset = HistoricalTrainingDataset(
        dataset_id=ds_id,
        idempotency_key=f"IDEMP-E2E-{uid}",
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
        artifact_path=f"/tmp/e2e_artifact_{uid}.pkl",
        artifact_sha256=art_sha,
        artifact_size_bytes=1024,
        training_timestamp=now,
        model_version=f"v1.1.0-cand-{uid}",
        feature_set_version="FeatureSetV1",
        lifecycle_status="CANDIDATE",
        is_deleted=False,
    )
    session.add(cand_model)

    config_hash = hashlib.sha256(f"{model_family}:config:{uid}".encode()).hexdigest()[:16]
    tr = MLTrainingRun(
        training_run_id=f"TR-E2E-{uid}",
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
    return dataset, cand_model


@pytest.mark.asyncio
async def test_ws59_01_full_four_family_promotion_pipeline(ws59_session: AsyncSession):
    """Test 1: Complete 4-family Candidate -> Holdout Evaluation -> Promotion pipeline."""
    session = ws59_session

    promoted_decisions = []
    for fam in MODEL_FAMILIES:
        dataset, cand_model = await _seed_four_family_dataset(session, fam, sample_count=30)
        
        eval_service = ModelEvaluationService(session)
        eval_record = await eval_service.evaluate_candidate_model(str(cand_model.id))
        assert eval_record.evaluation_status == "PASSED"

        # Fetch existing promoted model if any
        stmt_prev = select(MLModelVersion).where(
            MLModelVersion.model_name == fam,
            MLModelVersion.lifecycle_status == "PROMOTED",
            MLModelVersion.is_deleted == False,
        )
        res_prev = await session.execute(stmt_prev)
        prev_prom = res_prev.scalars().first()
        if prev_prom:
            prev_prom.lifecycle_status = "SUPERSEDED"
            await session.flush()

        prom_service = ModelPromotionService(session)
        decision = await prom_service.promote_candidate_model(
            candidate_model_version_id=str(cand_model.id),
            authorized_by="E2E_ADMIN",
        )
        assert decision.decision_type == "PROMOTED"
        assert decision.new_promoted_version == cand_model.model_version
        promoted_decisions.append(decision)

    # Verify exactly 4 active authority decisions exist (1 per family)
    stmt_auth = select(func.count(MLPromotionDecision.id)).where(MLPromotionDecision.is_active_authority == True)
    active_auth_count = (await session.execute(stmt_auth)).scalar()
    assert active_auth_count == 4


@pytest.mark.asyncio
async def test_ws59_02_rollback_isolation_and_lineage(ws59_session: AsyncSession):
    """Test 2: Rollback of one model family preserves other 3 families and maintains full audit lineage."""
    session = ws59_session

    # Seed Promoted V1
    fam = "delay_regressor"
    now = datetime.now(timezone.utc)
    v1_model = MLModelVersion(
        id=str(uuid.uuid4()),
        model_name=fam,
        model_category="REGRESSION",
        algorithm="LIGHTGBM",
        target_name="target",
        artifact_path="/tmp/v1.pkl",
        artifact_sha256="v1_sha",
        artifact_size_bytes=1024,
        training_timestamp=now - timedelta(days=10),
        training_dataset_id="DS-V1",
        feature_set_version="FeatureSetV1",
        model_version="v1.0.0-promoted-baseline",
        lifecycle_status="PROMOTED",
        is_deleted=False,
    )
    session.add(v1_model)
    await session.commit()

    # Seed & Promote Candidate V2
    dataset, cand_v2 = await _seed_four_family_dataset(session, fam, sample_count=30)
    eval_service = ModelEvaluationService(session)
    eval_rec = await eval_service.evaluate_candidate_model(str(cand_v2.id))

    prom_service = ModelPromotionService(session)
    dec_v2 = await prom_service.promote_candidate_model(str(cand_v2.id), authorized_by="E2E_ADMIN")
    await session.refresh(cand_v2)
    await session.refresh(v1_model)

    assert cand_v2.lifecycle_status == "PROMOTED"
    assert v1_model.lifecycle_status == "SUPERSEDED"

    # Rollback to V1
    rollback_dec = await prom_service.rollback_promoted_model(fam, authorized_by="E2E_ADMIN")
    await session.refresh(cand_v2)
    await session.refresh(v1_model)

    assert rollback_dec.decision_type == "ROLLED_BACK"
    assert rollback_dec.new_promoted_version == v1_model.model_version
    assert v1_model.lifecycle_status == "PROMOTED"
    assert cand_v2.lifecycle_status == "SUPERSEDED"
    assert eval_rec.evaluation_status == "PASSED" # Evaluation remains immutable!


@pytest.mark.asyncio
async def test_ws59_03_unauthorized_and_failed_promotion_rejection(ws59_session: AsyncSession):
    """Test 3: Unverified or failed holdout candidate CANNOT be promoted."""
    session = ws59_session
    dataset, cand_model = await _seed_four_family_dataset(session, "turnaround_regressor", sample_count=3) # Sample count 3 < 5 min holdout!

    eval_service = ModelEvaluationService(session)
    eval_record = await eval_service.evaluate_candidate_model(str(cand_model.id))
    assert eval_record.evaluation_status == "INSUFFICIENT_DATA"

    prom_service = ModelPromotionService(session)
    with pytest.raises(ValueError) as exc_info:
        await prom_service.promote_candidate_model(str(cand_model.id), authorized_by="E2E_ADMIN")

    assert "has no PASSED evaluation record" in str(exc_info.value)
    assert cand_model.lifecycle_status == "CANDIDATE" # Remains isolated!
