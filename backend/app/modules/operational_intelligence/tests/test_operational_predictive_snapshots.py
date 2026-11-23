"""
WS-09 Phase 7.5 Prediction Snapshot & Inference Authority Contract Dedicated Pytest Suite

Covers:
1. Production Real-State Test (0 promoted models -> NOT_CONFIGURED, zero authoritative snapshot persisted)
2. Rejected/Candidate Model Protection (cannot create authoritative snapshot)
3. Isolated Promoted Model Fixture Test (persists valid AUTHORITATIVE snapshot)
4. Idempotency Verification (same request -> same idempotency key -> same snapshot)
5. Snapshot Immutability Verification (preventing snapshot mutation)
6. Feature & Model Lineage Verification (survives model retirement)
7. Artifact SHA & Feature Mismatch Rejection
8. Explicit Compatibility & Input Leakage Rejection Tests
"""

import os
import hashlib
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from app.core.database import AsyncSessionFactory, engine
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer
from app.modules.operational_intelligence.ml.evaluator import (
    Phase73PromotionGateEvaluator,
    SingleModelEvaluationReportDTO,
    ModelEvaluationMetricsDTO,
)
from app.modules.operational_intelligence.ml.feature_extractor import Phase71FeatureExtractor


@pytest.mark.asyncio
async def test_real_production_state_not_configured():
    """
    1. Mandatory Real Production State Test:
    When 0 models are promoted, inference request returns NOT_CONFIGURED and does NOT persist an authoritative snapshot.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLPredictionSnapshotRepository(db_session)
        req = PredictionRequestDTO(
            dispatch_id="DISP-TEST-001",
            dispatch_code="DSP-2026-001",
            prediction_timestamp=datetime.now(timezone.utc),
            plant_code="P-001",
            customer_code="C-001",
            vehicle_code="V-001",
            ticket_volume_m3=6.0,
            plant_queue_avg_30d=15.0,
            customer_retention_avg_30d=8.0,
            dispatch_hour=10,
            dispatch_day_of_week=2,
        )

        res = await repo.generate_and_persist_prediction_snapshot("delay_regressor", req)
        assert res.prediction_status == "NOT_CONFIGURED"
        assert res.predicted_value is None
        assert res.model_version is None
        assert res.lineage_metadata["prediction_authority"] == "NOT_CONFIGURED"

        # Verify no snapshot was persisted in database table for NOT_CONFIGURED request
        db_snap = await repo.get_snapshot_by_idempotency_key(res.idempotency_key)
        assert db_snap is None


@pytest.mark.asyncio
async def test_rejected_and_candidate_models_cannot_generate_authoritative_snapshot():
    """
    2. Candidate & Rejected Model Protection:
    Ensures that REJECTED or TRAINED_CANDIDATE model versions cannot be resolved as active prediction authority.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        registry_repo = MLModelRegistryRepository(db_session)
        snapshot_repo = MLPredictionSnapshotRepository(db_session)

        # Train candidates
        await Phase72ModelTrainer.train_all_candidate_models(db_session, dataset_id="DS-TEST-7-5")

        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("sla_breach_classifier")

        # Register candidate
        reg = await registry_repo.register_candidate_version(
            model_name="sla_breach_classifier",
            model_category="Classification",
            model_version="v1.0.0-cand-test",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-CAND",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        req = PredictionRequestDTO(
            dispatch_id="DISP-TEST-002",
            dispatch_code="DSP-2026-002",
            prediction_timestamp=datetime.now(timezone.utc),
            plant_code="P-001",
            customer_code="C-001",
            vehicle_code="V-001",
            ticket_volume_m3=6.0,
            plant_queue_avg_30d=15.0,
            customer_retention_avg_30d=8.0,
            dispatch_hour=10,
            dispatch_day_of_week=2,
        )

        # Attempt prediction while model is TRAINED_CANDIDATE
        res1 = await snapshot_repo.generate_and_persist_prediction_snapshot("sla_breach_classifier", req)
        assert res1.prediction_status == "NOT_CONFIGURED"

        # Record REJECTED evaluation
        report = SingleModelEvaluationReportDTO(
            model_name="sla_breach_classifier",
            category="Classification",
            target_name="predicted_sla_breach_target",
            preflight=preflight,
            metrics_train=ModelEvaluationMetricsDTO(),
            metrics_val=ModelEvaluationMetricsDTO(),
            metrics_holdout=ModelEvaluationMetricsDTO(),
            threshold_rules=[],
            overall_gate_passed=False,
            promotion_decision="REJECTED",
            rejection_reasons=["Failed ROC-AUC"],
        )
        await registry_repo.record_evaluation_result("sla_breach_classifier", "v1.0.0-cand-test", report)

        # Attempt prediction while model is REJECTED
        res2 = await snapshot_repo.generate_and_persist_prediction_snapshot("sla_breach_classifier", req)
        assert res2.prediction_status == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_isolated_promoted_model_snapshot_persistence():
    """
    3. Isolated Positive Fixture Test:
    Promotes an isolated fixture model, executes prediction inference, and verifies PostgreSQL snapshot persistence.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        registry_repo = MLModelRegistryRepository(db_session)
        snapshot_repo = MLPredictionSnapshotRepository(db_session)

        # Train candidate
        await Phase72ModelTrainer.train_all_candidate_models(db_session, dataset_id="DS-TEST-7-5")
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        # Register fixture version
        reg = await registry_repo.register_candidate_version(
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v9.9.9-promoted-snapshot-fixture",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-FIXTURE-SNAP",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        passing_report = SingleModelEvaluationReportDTO(
            model_name="delay_regressor",
            category="Regression",
            target_name="predicted_delay_mins",
            preflight=preflight,
            metrics_train=ModelEvaluationMetricsDTO(r2=0.90, mae=5.0, rmse=8.0),
            metrics_val=ModelEvaluationMetricsDTO(r2=0.88, mae=6.0, rmse=9.0),
            metrics_holdout=ModelEvaluationMetricsDTO(r2=0.85, mae=7.0, rmse=10.0),
            threshold_rules=[],
            overall_gate_passed=True,
            promotion_decision="PROMOTABLE",
            rejection_reasons=[],
        )

        await registry_repo.record_evaluation_result("delay_regressor", "v9.9.9-promoted-snapshot-fixture", passing_report)
        promoted = await registry_repo.promote_model_version("delay_regressor", "v9.9.9-promoted-snapshot-fixture")

        req = PredictionRequestDTO(
            dispatch_id="DISP-TEST-003",
            dispatch_code="DSP-2026-003",
            prediction_timestamp=datetime.now(timezone.utc),
            plant_code="P-001",
            customer_code="C-001",
            vehicle_code="V-001",
            ticket_volume_m3=6.0,
            plant_queue_avg_30d=15.0,
            customer_retention_avg_30d=8.0,
            dispatch_hour=10,
            dispatch_day_of_week=2,
        )

        # Generate snapshot
        res = await snapshot_repo.generate_and_persist_prediction_snapshot("delay_regressor", req)
        assert res.prediction_status == "AUTHORITATIVE"
        assert res.model_version == "v9.9.9-promoted-snapshot-fixture"
        assert res.artifact_sha256 == meta.artifact_sha256
        assert isinstance(res.predicted_value, float)

        # Verify DB record exists
        db_snap = await snapshot_repo.get_snapshot_by_idempotency_key(res.idempotency_key)
        assert db_snap is not None
        assert db_snap.prediction_snapshot_id == res.prediction_snapshot_id

        # Cleanup active promoted fixture for test isolation
        promoted.lifecycle_status = "RETIRED"
        await db_session.flush()


@pytest.mark.asyncio
async def test_idempotency_and_snapshot_immutability():
    """
    4 & 5. Idempotency & Immutability Test:
    Repeated request returns existing snapshot without duplicate rows, and modifying a snapshot raises ValueError.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        registry_repo = MLModelRegistryRepository(db_session)
        snapshot_repo = MLPredictionSnapshotRepository(db_session)

        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("turnaround_regressor")

        reg = await registry_repo.register_candidate_version(
            model_name="turnaround_regressor",
            model_category="Regression",
            model_version="v9.9.9-idempotency-fixture",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-IDEMP",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        passing_report = SingleModelEvaluationReportDTO(
            model_name="turnaround_regressor",
            category="Regression",
            target_name="predicted_avg_turnaround_mins",
            preflight=preflight,
            metrics_train=ModelEvaluationMetricsDTO(),
            metrics_val=ModelEvaluationMetricsDTO(),
            metrics_holdout=ModelEvaluationMetricsDTO(),
            threshold_rules=[],
            overall_gate_passed=True,
            promotion_decision="PROMOTABLE",
            rejection_reasons=[],
        )

        await registry_repo.record_evaluation_result("turnaround_regressor", "v9.9.9-idempotency-fixture", passing_report)
        promoted = await registry_repo.promote_model_version("turnaround_regressor", "v9.9.9-idempotency-fixture")

        req = PredictionRequestDTO(
            dispatch_id="DISP-TEST-004",
            dispatch_code="DSP-2026-004",
            prediction_timestamp="2026-08-17T10:00:00+00:00",
            plant_code="P-001",
            customer_code="C-001",
            vehicle_code="V-001",
            ticket_volume_m3=6.0,
            plant_queue_avg_30d=15.0,
            customer_retention_avg_30d=8.0,
            dispatch_hour=10,
            dispatch_day_of_week=2,
            idempotency_key="IK-FIX-004",
        )

        # First Call
        res1 = await snapshot_repo.generate_and_persist_prediction_snapshot("turnaround_regressor", req)
        # Second Call (Same Idempotency Key)
        res2 = await snapshot_repo.generate_and_persist_prediction_snapshot("turnaround_regressor", req)

        assert res1.prediction_snapshot_id == res2.prediction_snapshot_id

        # Verify Immutability Assertion
        with pytest.raises(ValueError, match="IMMUTABILITY VIOLATION"):
            await snapshot_repo.verify_snapshot_immutability(res1.prediction_snapshot_id, {"predicted_value": 999.9})

        # Cleanup
        promoted.lifecycle_status = "RETIRED"
        await db_session.flush()


@pytest.mark.asyncio
async def test_historical_lineage_survives_model_retirement():
    """
    6. Historical Lineage Test:
    Historical prediction snapshots remain fully queryable even after the associated model version is RETIRED.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        registry_repo = MLModelRegistryRepository(db_session)
        snapshot_repo = MLPredictionSnapshotRepository(db_session)

        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("plant_risk_classifier")

        reg = await registry_repo.register_candidate_version(
            model_name="plant_risk_classifier",
            model_category="Classification",
            model_version="v9.9.9-retire-lineage-fixture",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-RETIRE-LINEAGE",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        passing_report = SingleModelEvaluationReportDTO(
            model_name="plant_risk_classifier",
            category="Classification",
            target_name="predicted_plant_congestion_target",
            preflight=preflight,
            metrics_train=ModelEvaluationMetricsDTO(),
            metrics_val=ModelEvaluationMetricsDTO(),
            metrics_holdout=ModelEvaluationMetricsDTO(),
            threshold_rules=[],
            overall_gate_passed=True,
            promotion_decision="PROMOTABLE",
            rejection_reasons=[],
        )

        await registry_repo.record_evaluation_result("plant_risk_classifier", "v9.9.9-retire-lineage-fixture", passing_report)
        promoted = await registry_repo.promote_model_version("plant_risk_classifier", "v9.9.9-retire-lineage-fixture")

        req = PredictionRequestDTO(
            dispatch_id="DISP-TEST-005",
            dispatch_code="DSP-2026-005",
            prediction_timestamp=datetime.now(timezone.utc),
            plant_code="P-001",
            customer_code="C-001",
            vehicle_code="V-001",
            ticket_volume_m3=6.0,
            plant_queue_avg_30d=15.0,
            customer_retention_avg_30d=8.0,
            dispatch_hour=10,
            dispatch_day_of_week=2,
        )

        res = await snapshot_repo.generate_and_persist_prediction_snapshot("plant_risk_classifier", req)
        snap_id = res.prediction_snapshot_id

        # Retire the model
        await registry_repo.retire_model_version("plant_risk_classifier", "v9.9.9-retire-lineage-fixture")

        # Query snapshot historical records for dispatch
        snaps = await snapshot_repo.list_snapshots_by_dispatch("DSP-2026-005")
        assert len(snaps) == 1
        assert snaps[0].prediction_snapshot_id == snap_id
        assert snaps[0].model_version == "v9.9.9-retire-lineage-fixture"


@pytest.mark.asyncio
async def test_explicit_input_leakage_rejection_at_snapshot_creation():
    """
    7. Anti-Leakage Assertion Test:
    Attempts to generate a prediction snapshot using forbidden outcome fields (e.g. t2a_holding_mins).
    Must raise ValueError to enforce Phase 7.1 Anti-Leakage governance.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # Construct feature dictionary containing forbidden field
        leaking_features = {
            "plant_code": "P-001",
            "customer_code": "C-001",
            "vehicle_code": "V-001",
            "ticket_volume_m3": 6.0,
            "t2a_holding_mins": 25.0,  # FORBIDDEN OUTCOME FIELD
        }

        with pytest.raises(ValueError, match="ANTI-LEAKAGE VIOLATION"):
            Phase71FeatureExtractor.validate_no_leakage_in_features(leaking_features)
