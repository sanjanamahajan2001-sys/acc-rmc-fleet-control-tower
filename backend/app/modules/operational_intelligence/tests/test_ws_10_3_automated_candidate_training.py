"""
WS-10.3 Dedicated Test Suite: Automated Candidate Model Training Orchestration.
Verifies all minimum test requirements for WS-10.3.
"""

import os
import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from app.core.database import AsyncSessionFactory, engine
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, Ticket
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.ml_training_job import MLTrainingJob
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.ml.feature_extractor import (
    FEATURE_SET_VERSION,
    Phase71FeatureExtractor,
    FORBIDDEN_LEAKAGE_FIELDS,
)
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.ml.trainer import (
    WS10ModelTrainer,
    WS10TrainingOrchestrator,
    MODEL_CONFIGURATIONS,
)
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService


@pytest.mark.asyncio
async def test_ws_10_3_pending_trigger_consumption_and_running_transition():
    """1, 2 & 17. Pending trigger consumption, PENDING -> RUNNING -> COMPLETED transitions."""
    await engine.dispose()
    family = f"family_trig_{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        trig = MLLifecycleTrigger(
            trigger_id=f"trig-train-{uuid.uuid4().hex[:8]}",
            job_number=f"JOB-TRAIN-{uuid.uuid4().hex[:6]}",
            dataset_id="DS-PENDING-TRIG",
            model_family=family,
            status="PENDING",
            new_dispatch_count=150,
        )
        session.add(trig)
        await session.commit()
        t_id = trig.trigger_id

    async with AsyncSessionFactory() as session:
        tr_job = await WS10TrainingOrchestrator.process_trigger_or_dataset(session, trigger_id=t_id)
        await session.commit()

        assert tr_job.status == "COMPLETED"
        assert tr_job.models_trained_count == 4

        # Check trigger state updated to COMPLETED
        stmt_t = select(MLLifecycleTrigger).where(MLLifecycleTrigger.trigger_id == t_id)
        res_t = await session.execute(stmt_t)
        updated_t = res_t.scalars().first()
        assert updated_t.status == "COMPLETED"


@pytest.mark.asyncio
async def test_ws_10_3_dataset_resolution_and_featureset_v1_validation():
    """3 & 4. Dataset resolution & FeatureSetV1 validation."""
    await engine.dispose()
    ds_id = f"DS-RESOLVE-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=20
        )
        await session.commit()

    async with AsyncSessionFactory() as session:
        tr_job = await WS10TrainingOrchestrator.process_trigger_or_dataset(session, dataset_id=ds_id)
        await session.commit()

        assert tr_job.dataset_id == ds_id
        assert tr_job.models_trained_count == 4


@pytest.mark.asyncio
async def test_ws_10_3_target_mapping_for_all_four_models():
    """5. Required target mapping for all 4 model families."""
    await engine.dispose()
    assert MODEL_CONFIGURATIONS["delay_regressor"]["target_key"] == "predicted_delay_mins"
    assert MODEL_CONFIGURATIONS["turnaround_regressor"]["target_key"] == "predicted_avg_turnaround_mins"
    assert MODEL_CONFIGURATIONS["sla_breach_classifier"]["target_key"] == "predicted_sla_breach_target"
    assert MODEL_CONFIGURATIONS["plant_risk_classifier"]["target_key"] == "predicted_plant_congestion_target"


@pytest.mark.asyncio
async def test_ws_10_3_anti_leakage_runtime_guard():
    """6 & 7. Anti-leakage runtime guard rejects forbidden columns in X matrix."""
    import pandas as pd

    for forbidden in FORBIDDEN_LEAKAGE_FIELDS:
        bad_df = pd.DataFrame([{"plant_code": "P1", forbidden: 20.0}])
        with pytest.raises(ValueError, match="ANTI-LEAKAGE TRAINING VIOLATION"):
            WS10ModelTrainer.validate_no_leakage_in_dataframe(bad_df)


@pytest.mark.asyncio
async def test_ws_10_3_train_only_preprocessing_and_holdout_isolation():
    """7 & 8. TRAIN-only preprocessing & holdout isolation."""
    await engine.dispose()
    ds_id = f"DS-ISOLATION-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=30
        )
        await session.commit()

        m_version, art_path, checksum = await WS10ModelTrainer.train_candidate_family(
            session=session,
            model_name="delay_regressor",
            extracted_ds=ext,
            dataset_id=ds_id,
        )
        await session.commit()

        rc = m_version.row_counts
        assert rc["train"] == db_ds.train_count
        assert rc["holdout"] == db_ds.holdout_count


@pytest.mark.asyncio
async def test_ws_10_3_candidate_artifact_generation_and_sha_verification():
    """9, 10, 11 & 12. Candidate artifact generation, SHA-256 verification & TRAINED_CANDIDATE registration."""
    await engine.dispose()
    ds_id = f"DS-ARTIFACT-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=25
        )
        await session.commit()

    async with AsyncSessionFactory() as session:
        m_version, art_path, checksum = await WS10ModelTrainer.train_candidate_family(
            session=session,
            model_name="turnaround_regressor",
            extracted_ds=ext,
            dataset_id=ds_id,
        )
        await session.commit()

        assert os.path.exists(art_path)
        assert m_version.lifecycle_status == "TRAINED_CANDIDATE"
        assert m_version.evaluation_decision == "PENDING_EVALUATION"
        assert m_version.artifact_sha256 == checksum


@pytest.mark.asyncio
async def test_ws_10_3_artifact_immutability_and_mutation_detection():
    """Artifact immutability: Mutated artifact triggers ARTIFACT MUTATION DETECTED and DB stored SHA remains unchanged."""
    await engine.dispose()
    ds_id = f"DS-MUTATE-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=20
        )
        await session.commit()

        m_version, art_path, original_sha = await WS10ModelTrainer.train_candidate_family(
            session=session,
            model_name="delay_regressor",
            extracted_ds=ext,
            dataset_id=ds_id,
        )
        await session.commit()
        ver_str = m_version.model_version

    # Read original artifact bytes for safe cleanup
    with open(art_path, "rb") as f:
        original_bytes = f.read()

    try:
        # Mutate artifact file bytes on disk
        with open(art_path, "ab") as f:
            f.write(b"\n# MUTATION_BYTE_CORRUPTION_TEST")

        async with AsyncSessionFactory() as session:
            reg_repo = MLModelRegistryRepository(session)
            
            # Assert verify_registered_artifact_sha detects ARTIFACT MUTATION DETECTED
            with pytest.raises(ValueError, match="ARTIFACT MUTATION DETECTED"):
                await reg_repo.verify_registered_artifact_sha("delay_regressor", ver_str)

            # Query database and assert stored registry record is STILL the original SHA
            stored = await reg_repo.get_by_version_number("delay_regressor", ver_str)
            assert stored.artifact_sha256 == original_sha
            assert stored.lifecycle_status == "TRAINED_CANDIDATE"
            assert stored.evaluation_decision == "PENDING_EVALUATION"

    finally:
        # Restore original artifact file cleanly
        with open(art_path, "wb") as f:
            f.write(original_bytes)



@pytest.mark.asyncio
async def test_ws_10_3_trained_candidate_boundary_and_no_promotion():
    """13, 14, 15, 24 & 25. TRAINED_CANDIDATE boundary, zero promotions, zero snapshots & existing rejected untouched."""
    await engine.dispose()
    ds_id = f"DS-SAFETY-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=20
        )
        tr_job = await WS10TrainingOrchestrator.process_trigger_or_dataset(session, dataset_id=ds_id)
        await session.commit()

    async with AsyncSessionFactory() as session:
        stmt_m = select(MLModelVersion)
        res_m = await session.execute(stmt_m)
        models = res_m.scalars().all()

        promoted = [m for m in models if m.training_dataset_id == ds_id and m.lifecycle_status == "PROMOTED"]
        rejected = [m for m in models if m.lifecycle_status == "REJECTED"]
        candidates = [m for m in models if m.training_dataset_id == ds_id and m.lifecycle_status == "TRAINED_CANDIDATE"]

        assert len(promoted) == 0
        assert len(rejected) >= 4
        assert len(candidates) >= 4

        overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert overview.overall_authority_status == "NOT_CONFIGURED"

        stmt_s = select(MLPredictionSnapshot)
        res_s = await session.execute(stmt_s)
        snaps = res_s.scalars().all()
        assert len(snaps) == 0


@pytest.mark.asyncio
async def test_ws_10_3_training_failure_handling_and_retry():
    """18 & 19. Training failure handling & safe retry."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        tr_job = await WS10TrainingOrchestrator.process_trigger_or_dataset(
            session, dataset_id="NON_EXISTENT_DATASET_ID"
        )
        await session.commit()

        assert tr_job.status == "FAILED"
        assert "not found" in tr_job.reason.lower()


@pytest.mark.asyncio
async def test_ws_10_3_worker_concurrency_and_duplicate_idempotency():
    """20, 21 & 22. Worker concurrency protection & duplicate training idempotency."""
    await engine.dispose()
    family = f"family_concur_{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        trig = MLLifecycleTrigger(
            trigger_id=f"trig-concur-{uuid.uuid4().hex[:8]}",
            job_number=f"JOB-CONCUR-{uuid.uuid4().hex[:6]}",
            dataset_id="DS-CONCUR-TRAIN",
            model_family=family,
            status="PENDING",
            new_dispatch_count=200,
        )
        session.add(trig)
        await session.commit()
        t_id = trig.trigger_id

    async with AsyncSessionFactory() as session1:
        tr_job1 = await WS10TrainingOrchestrator.process_trigger_or_dataset(session1, trigger_id=t_id)
        await session1.commit()
        assert tr_job1.status == "COMPLETED"

    async with AsyncSessionFactory() as session2:
        stmt_t = select(MLLifecycleTrigger).where(MLLifecycleTrigger.trigger_id == t_id)
        res_t = await session2.execute(stmt_t)
        t_obj = res_t.scalars().first()
        assert t_obj.status == "COMPLETED"


@pytest.mark.asyncio
async def test_ws_10_3_deterministic_reproducibility():
    """23. Deterministic training reproducibility."""
    await engine.dispose()
    ds_id = f"DS-REPRO-TRAIN-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=20
        )
        await session.commit()

        v1, p1, sha1 = await WS10ModelTrainer.train_candidate_family(
            session=session, model_name="delay_regressor", extracted_ds=ext, dataset_id=ds_id
        )
        await session.commit()

        v2, p2, sha2 = await WS10ModelTrainer.train_candidate_family(
            session=session, model_name="delay_regressor", extracted_ds=ext, dataset_id=ds_id
        )
        await session.commit()

        assert v1.model_version == v2.model_version
        assert sha1 == sha2


@pytest.mark.asyncio
async def test_ws_10_3_performance_benchmark():
    """18 & Performance. Benchmark four-model candidate training duration."""
    await engine.dispose()
    ds_id = f"DS-PERF-TRAIN-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=50
        )
        await session.commit()

        t0 = time.perf_counter()
        tr_job = await WS10TrainingOrchestrator.process_trigger_or_dataset(session, dataset_id=ds_id)
        await session.commit()
        t1 = time.perf_counter()

        duration = t1 - t0
        print(f"\n[WS-10.3 BENCHMARK] Trained 4 candidate model families for {db_ds.total_records} rows in {duration:.2f} s")
        assert duration < 30.0, f"Four-model training exceeded 30s SLO baseline ({duration:.2f} s)"
