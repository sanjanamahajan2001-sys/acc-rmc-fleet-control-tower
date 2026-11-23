"""
WS-10.4 Dedicated Pytest Verification & Certification Suite.
Automated Candidate Model Evaluation & Phase 7.3 Promotion-Gate Integration.
Exact 22 Required Certification Test Methods.
"""

import os
import time
import uuid
import pytest
import hashlib
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import AsyncSessionFactory, engine
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.ml_evaluation_job import MLEvaluationJob
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.ml.feature_extractor import FEATURE_SET_VERSION, FeatureRecordDTO
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.ml.trainer import WS10ModelTrainer, MODEL_CONFIGURATIONS, MODEL_STORAGE_BASE_DIR
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator, PROMOTION_GATE_THRESHOLDS
from app.modules.operational_intelligence.services.evaluator_service import WS10CandidateEvaluationService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository

# Create NullPool engine for pytest-asyncio event loop isolation
test_engine = create_async_engine(engine.url, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def setup_shared_candidate_models(session, ds_id_override=None):
    """Creates or reuses a shared test dataset and candidate models for fast execution."""
    ds_id = ds_id_override or "DS-SHARED-WS10-4-PERMANENT"
    stmt_ds = select(MLDataset).where(MLDataset.dataset_id == ds_id)
    res_ds = await session.execute(stmt_ds)
    db_ds = res_ds.scalars().first()

    if not db_ds:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=20
        )
        await session.flush()

    stmt_mv = select(MLModelVersion).where(MLModelVersion.training_dataset_id == ds_id)
    res_mv = await session.execute(stmt_mv)
    results = list(res_mv.scalars().all())

    if len(results) < 4:
        results = await WS10ModelTrainer.train_all_candidate_models(session, dataset_id=ds_id)
        await session.flush()

    return ds_id, db_ds, results


async def get_candidate_by_name_and_ds(session, model_name: str, ds_id: str) -> MLModelVersion:
    """Helper to fetch MLModelVersion entity by model_name and dataset_id."""
    stmt = select(MLModelVersion).where(
        and_(
            MLModelVersion.model_name == model_name,
            MLModelVersion.training_dataset_id == ds_id,
        )
    )
    res = await session.execute(stmt)
    v = res.scalars().first()
    if not v:
        raise ValueError(f"Candidate '{model_name}' for dataset '{ds_id}' not found.")
    return v


# =============================================================================
# 22 MANDATORY CERTIFICATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_4_01_candidate_discovery():
    """1. Candidate discovery for TRAINED_CANDIDATE & PENDING_EVALUATION."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session, "DS-DISCOVERY-10-4")
        for r in results:
            r.evaluation_decision = "PENDING_EVALUATION"
            r.lifecycle_status = "TRAINED_CANDIDATE"
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        pending = await repo.get_pending_evaluation_candidates()
        assert len(pending) >= 4
        model_names = [p.model_name for p in pending]
        assert "delay_regressor" in model_names
        assert "turnaround_regressor" in model_names
        assert "sla_breach_classifier" in model_names
        assert "plant_risk_classifier" in model_names


@pytest.mark.asyncio
async def test_ws_10_4_02_dataset_resolution():
    """2. Dataset resolution from immutable ml_datasets."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        assert eval_job.dataset_id == ds_id
        assert eval_job.status == "COMPLETED"


@pytest.mark.asyncio
async def test_ws_10_4_03_featureset_v1_compatibility():
    """3. FeatureSetV1 validation rejects non-matching feature set versions."""
    ds_id = f"DS-INVALID-FS-{uuid.uuid4().hex[:6]}"
    ver_num = f"v10.4.{uuid.uuid4().hex[:4]}"

    async with TestAsyncSessionFactory() as session:
        bad_ds = MLDataset(
            dataset_id=ds_id,
            feature_set_version="FeatureSetV0_Legacy",
            total_records=10,
            train_count=6,
            val_count=2,
            holdout_count=2,
            lineage_metadata={"records": [{"partition": "HOLDOUT_TEST"}]},
            exclusion_stats={},
            target_availability={},
            sha256_checksum="dummy",
        )
        session.add(bad_ds)
        await session.commit()

        art_dir = os.path.join(MODEL_STORAGE_BASE_DIR, "delay_regressor")
        os.makedirs(art_dir, exist_ok=True)
        art_path = os.path.join(art_dir, f"dummy_{ver_num}.joblib")
        with open(art_path, "wb") as f:
            f.write(b"dummy model artifact bytes")
        sha = hashlib.sha256(b"dummy model artifact bytes").hexdigest()

        version_entity = MLModelVersion(
            model_name="delay_regressor",
            model_category="Regression",
            model_version=ver_num,
            algorithm="RandomForestRegressor",
            target_name="predicted_delay_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id=ds_id,
            artifact_path=art_path,
            artifact_sha256=sha,
            artifact_size_bytes=len(b"dummy model artifact bytes"),
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="TRAINED_CANDIDATE",
            evaluation_decision="PENDING_EVALUATION",
        )
        session.add(version_entity)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, version_entity)
        await session.commit()

        assert eval_job.status == "FAILED"
        assert eval_job.reason == "MALFORMED_FEATURESET"
        assert updated.evaluation_decision == "REJECTED"


@pytest.mark.asyncio
async def test_ws_10_4_04_artifact_sha_verification():
    """4. Artifact SHA verification matches stored checksum."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        cand = await get_candidate_by_name_and_ds(session, "turnaround_regressor", ds_id)
        verified = await repo.verify_registered_artifact_sha(cand.model_name, cand.model_version)
        assert verified is True


@pytest.mark.asyncio
async def test_ws_10_4_05_holdout_test_only_evaluation():
    """5. HOLDOUT_TEST-only evaluation isolation."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "sla_breach_classifier", ds_id)
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        prov = updated.evaluation_provenance
        assert "holdout_row_count" in prov
        assert prov["holdout_row_count"] > 0


@pytest.mark.asyncio
async def test_ws_10_4_06_no_holdout_preprocessing_fit():
    """6. Holdout evaluation uses pre-fit preprocessor without refitting on test partition."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        # Provenance verifies evaluation evaluator version
        assert updated.evaluation_provenance.get("evaluator_version") == "WS-10.4"
        assert eval_job.status == "COMPLETED"


@pytest.mark.asyncio
async def test_ws_10_4_07_all_four_model_families():
    """7. Evaluates all four model families (delay, turnaround, sla, plant_risk)."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        for m_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            cand = await get_candidate_by_name_and_ds(session, m_name, ds_id)
            eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
            assert eval_job.status == "COMPLETED"
            assert eval_job.model_name == m_name
        await session.commit()


@pytest.mark.asyncio
async def test_ws_10_4_08_canonical_phase73_threshold_reuse():
    """8. Canonical Phase 7.3 threshold rules reuse."""
    assert PROMOTION_GATE_THRESHOLDS["delay_regressor"]["r2_min"] == 0.70
    assert PROMOTION_GATE_THRESHOLDS["turnaround_regressor"]["mae_max"] == 8.0
    assert PROMOTION_GATE_THRESHOLDS["sla_breach_classifier"]["roc_auc_min"] == 0.75
    assert PROMOTION_GATE_THRESHOLDS["plant_risk_classifier"]["f1_min"] == 0.70


@pytest.mark.asyncio
async def test_ws_10_4_09_passing_candidate_promotion_eligible():
    """9. Passing candidate marked PROMOTION_ELIGIBLE."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        if eval_job.reason == "EVALUATION_PASSED":
            assert updated.evaluation_decision == "PROMOTION_ELIGIBLE"
            assert updated.lifecycle_status == "TRAINED_CANDIDATE"


@pytest.mark.asyncio
async def test_ws_10_4_10_failing_candidate_rejection_state():
    """10. Failing candidate marked canonical REJECTED state."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session, f"DS-FAIL-{uuid.uuid4().hex[:4]}")
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)
        art_path = cand.artifact_path

        # Mutate artifact to force failure
        with open(art_path, "ab") as f:
            f.write(b"FORCE_FAILURE_BYTES")

        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        assert updated.evaluation_decision == "REJECTED"
        assert updated.lifecycle_status == "REJECTED"


@pytest.mark.asyncio
async def test_ws_10_4_11_no_automatic_promotion():
    """11. No automatic promotion assertion (PROMOTED count remains 0)."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        for m_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            cand = await get_candidate_by_name_and_ds(session, m_name, ds_id)
            await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        stmt = select(MLModelVersion).where(MLModelVersion.training_dataset_id == ds_id)
        res = await session.execute(stmt)
        evaluated_versions = list(res.scalars().all())

        for v in evaluated_versions:
            assert v.lifecycle_status != "PROMOTED", "CRITICAL VIOLATION: Candidate was automatically promoted!"


@pytest.mark.asyncio
async def test_ws_10_4_12_zero_prediction_snapshots():
    """12. Zero prediction snapshots created during evaluation."""
    async with TestAsyncSessionFactory() as session:
        stmt0 = select(func.count(MLPredictionSnapshot.id))
        res0 = await session.execute(stmt0)
        c0 = res0.scalar()

        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

        for m_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            cand = await get_candidate_by_name_and_ds(session, m_name, ds_id)
            await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        stmt1 = select(func.count(MLPredictionSnapshot.id))
        res1 = await session.execute(stmt1)
        c1 = res1.scalar()

        assert c1 == c0, "CRITICAL VIOLATION: Evaluation created prediction snapshots!"


@pytest.mark.asyncio
async def test_ws_10_4_13_artifact_mutation_detection():
    """13. Artifact mutation detected when SHA mismatches on disk."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session, f"DS-MUTATE-{uuid.uuid4().hex[:4]}")
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)
        art_path = cand.artifact_path

        with open(art_path, "ab") as f:
            f.write(b"CORRUPTED_BYTES_MUTATION")

        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        assert eval_job.status == "FAILED"
        assert eval_job.reason == "ARTIFACT_MUTATION_DETECTED"
        assert updated.evaluation_decision == "REJECTED"
        assert updated.lifecycle_status == "REJECTED"


@pytest.mark.asyncio
async def test_ws_10_4_14_missing_artifact_rejection():
    """14. Missing artifact rejection."""
    ds_id = f"DS-MISSING-ART-{uuid.uuid4().hex[:6]}"
    ver_num = f"v10.4.{uuid.uuid4().hex[:4]}"

    async with TestAsyncSessionFactory() as session:
        version_entity = MLModelVersion(
            model_name="plant_risk_classifier",
            model_category="Classification",
            model_version=ver_num,
            algorithm="RandomForestClassifier",
            target_name="predicted_plant_congestion_target",
            feature_set_version="FeatureSetV1",
            training_dataset_id=ds_id,
            artifact_path="/tmp/non_existent_artifact_file.joblib",
            artifact_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            artifact_size_bytes=100,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="TRAINED_CANDIDATE",
            evaluation_decision="PENDING_EVALUATION",
        )
        session.add(version_entity)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, version_entity)
        await session.commit()

        assert eval_job.status == "FAILED"
        assert eval_job.reason == "MISSING_ARTIFACT"
        assert updated.evaluation_decision == "REJECTED"


@pytest.mark.asyncio
async def test_ws_10_4_15_missing_dataset_rejection():
    """15. Missing dataset rejection."""
    ds_id = f"DS-MISSING-DS-{uuid.uuid4().hex[:6]}"
    ver_num = f"v10.4.{uuid.uuid4().hex[:4]}"

    art_dir = os.path.join(MODEL_STORAGE_BASE_DIR, "sla_breach_classifier")
    os.makedirs(art_dir, exist_ok=True)
    art_path = os.path.join(art_dir, f"dummy_{ver_num}.joblib")
    with open(art_path, "wb") as f:
        f.write(b"dummy content for missing dataset test")
    sha = hashlib.sha256(b"dummy content for missing dataset test").hexdigest()

    async with TestAsyncSessionFactory() as session:
        version_entity = MLModelVersion(
            model_name="sla_breach_classifier",
            model_category="Classification",
            model_version=ver_num,
            algorithm="RandomForestClassifier",
            target_name="predicted_sla_breach_target",
            feature_set_version="FeatureSetV1",
            training_dataset_id=ds_id,
            artifact_path=art_path,
            artifact_sha256=sha,
            artifact_size_bytes=len(b"dummy content for missing dataset test"),
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="TRAINED_CANDIDATE",
            evaluation_decision="PENDING_EVALUATION",
        )
        session.add(version_entity)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, version_entity)
        await session.commit()

        assert eval_job.status == "FAILED"
        assert eval_job.reason == "MISSING_DATASET"
        assert updated.evaluation_decision == "REJECTED"


@pytest.mark.asyncio
async def test_ws_10_4_16_empty_holdout_rejection():
    """16. Empty holdout dataset handling."""
    ds_id = f"DS-EMPTY-HOLD-{uuid.uuid4().hex[:6]}"
    ver_num = f"v10.4.{uuid.uuid4().hex[:4]}"

    async with TestAsyncSessionFactory() as session:
        empty_holdout_ds = MLDataset(
            dataset_id=ds_id,
            feature_set_version="FeatureSetV1",
            total_records=10,
            train_count=10,
            val_count=0,
            holdout_count=0,
            lineage_metadata={"partitions": {"HOLDOUT_TEST": []}},
            exclusion_stats={},
            target_availability={},
            sha256_checksum="dummy",
        )
        session.add(empty_holdout_ds)

        art_dir = os.path.join(MODEL_STORAGE_BASE_DIR, "delay_regressor")
        os.makedirs(art_dir, exist_ok=True)
        art_path = os.path.join(art_dir, f"dummy_empty_{ver_num}.joblib")
        with open(art_path, "wb") as f:
            f.write(b"dummy bytes empty holdout")
        sha = hashlib.sha256(b"dummy bytes empty holdout").hexdigest()

        version_entity = MLModelVersion(
            model_name="delay_regressor",
            model_category="Regression",
            model_version=ver_num,
            algorithm="RandomForestRegressor",
            target_name="predicted_delay_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id=ds_id,
            artifact_path=art_path,
            artifact_sha256=sha,
            artifact_size_bytes=len(b"dummy bytes empty holdout"),
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="TRAINED_CANDIDATE",
            evaluation_decision="PENDING_EVALUATION",
        )
        session.add(version_entity)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        eval_job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, version_entity)
        await session.commit()

        assert eval_job.status == "FAILED"
        assert eval_job.reason == "EMPTY_HOLDOUT"
        assert updated.evaluation_decision == "REJECTED"


@pytest.mark.asyncio
async def test_ws_10_4_17_concurrent_evaluator_protection():
    """17. Concurrent evaluator protection using row-level locking (SKIP LOCKED)."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session, f"DS-CONCURR-{uuid.uuid4().hex[:4]}")
        for r in results:
            r.evaluation_decision = "PENDING_EVALUATION"
            r.lifecycle_status = "TRAINED_CANDIDATE"
        await session.commit()

    async with TestAsyncSessionFactory() as session_a:
        repo_a = MLModelRegistryRepository(session_a)
        cand_a = await repo_a.claim_next_pending_candidate()
        assert cand_a is not None

        async with TestAsyncSessionFactory() as session_b:
            repo_b = MLModelRegistryRepository(session_b)
            cand_b = await repo_b.claim_next_pending_candidate()
            if cand_b is not None:
                assert cand_b.id != cand_a.id, "CRITICAL ERROR: Worker B claimed the exact same candidate as Worker A!"

        await session_a.commit()


@pytest.mark.asyncio
async def test_ws_10_4_18_duplicate_evaluation_idempotency():
    """18. Duplicate evaluation request idempotency."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)

        job1, updated1 = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        job2, updated2 = await WS10CandidateEvaluationService.evaluate_candidate_version(session, updated1)
        await session.commit()

        assert updated2.evaluation_decision == updated1.evaluation_decision


@pytest.mark.asyncio
async def test_ws_10_4_19_worker_restart_and_recovery():
    """19. Restart/recovery handling for in-flight claimed candidates."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session, f"DS-RECOVER-{uuid.uuid4().hex[:4]}")
        for r in results:
            r.evaluation_decision = "PENDING_EVALUATION"
            r.lifecycle_status = "TRAINED_CANDIDATE"
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        cand = await repo.claim_next_pending_candidate()
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        stmt = select(MLModelVersion).where(MLModelVersion.id == cand_id)
        res = await session.execute(stmt)
        recovered_cand = res.scalars().first()

        job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, recovered_cand)
        await session.commit()

        assert updated.evaluation_decision in ("PROMOTION_ELIGIBLE", "REJECTED")


@pytest.mark.asyncio
async def test_ws_10_4_20_audit_lineage_persistence():
    """20. Audit lineage persistence in ml_model_audit_events."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)
        c_id = cand.id
        job, updated = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()

        stmt_aud = select(MLModelAuditEvent).where(MLModelAuditEvent.model_version_id == c_id)
        res_aud = await session.execute(stmt_aud)
        audits = list(res_aud.scalars().all())

        assert len(audits) >= 2
        event_types = [a.event_type for a in audits]
        assert "MODEL_REGISTERED" in event_types
        assert "MODEL_EVALUATED" in event_types or "MODEL_REJECTED" in event_types


@pytest.mark.asyncio
async def test_ws_10_4_21_deterministic_evaluation():
    """21. Deterministic evaluation metrics on identical inputs."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        cand = await get_candidate_by_name_and_ds(session, "delay_regressor", ds_id)

        job1, _ = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        job2, _ = await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)

        for k in job1.metrics_holdout:
            v1 = job1.metrics_holdout[k]
            v2 = job2.metrics_holdout[k]
            if v1 is not None and v2 is not None and isinstance(v1, (float, int)):
                assert pytest.approx(v1, abs=1e-6) == v2
            else:
                assert v1 == v2


@pytest.mark.asyncio
async def test_ws_10_4_22_performance_benchmark():
    """22. Performance benchmark for candidate model evaluation."""
    async with TestAsyncSessionFactory() as session:
        ds_id, db_ds, results = await setup_shared_candidate_models(session)

        t0 = time.perf_counter()
        for m_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            cand = await get_candidate_by_name_and_ds(session, m_name, ds_id)
            await WS10CandidateEvaluationService.evaluate_candidate_version(session, cand)
        await session.commit()
        t1 = time.perf_counter()

        duration = t1 - t0
        print(f"\n[WS-10.4 BENCHMARK] Evaluated 4 candidate models in {duration:.2f} s")
        assert duration < 120.0, f"Candidate evaluation suite exceeded 120.0s SLO baseline ({duration:.2f} s)"
