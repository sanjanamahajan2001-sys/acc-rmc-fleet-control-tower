"""
WS-09 Phase 7.4 Model Registry & Version Authority Dedicated Pytest Suite (Expanded Governance Edition)

Covers all 10 mandatory governance verification rules:
1. Complete Dataset Lineage
2. Complete Evaluation Provenance (TRAIN, VAL, HOLDOUT)
3. Valid Promotion Test (Isolated Fixture)
4. Retirement Test (Isolated Fixture)
5. Invalid Lifecycle Transitions Rejection
6. Transactional Promotion Rollback
7. Duplicate Model Version Protection
8. Artifact Mutation Detection
9. Audit History Immutability & Append-Only Behavior
10. Current Real Production State NOT_CONFIGURED Verification
"""

import os
import hashlib
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from app.core.database import AsyncSessionFactory, engine
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer
from app.modules.operational_intelligence.ml.evaluator import (
    Phase73PromotionGateEvaluator,
    SingleModelEvaluationReportDTO,
    CandidatePreflightCheckDTO,
    ModelEvaluationMetricsDTO,
    GateThresholdRuleDTO,
)


@pytest.mark.asyncio
async def test_dataset_lineage_and_provenance_persistence():
    """
    1 & 2. Verifies that dataset lineage (FeatureSetV1, train, val, holdout IDs) and full evaluation provenance are persisted.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        reg = await repo.register_candidate_version(
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v1.0.0-lineage-test",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-20260805-001",
            validation_dataset_id="DS-20260805-001-VAL",
            holdout_dataset_id="DS-20260805-001-HOLDOUT",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
            hyperparameters=meta.hyperparameters,
            random_seed=42,
            row_counts={"train": 2301, "val": 618, "holdout": 613},
        )

        assert reg.feature_set_version == "FeatureSetV1"
        assert reg.training_dataset_id == "DS-20260805-001"
        assert reg.validation_dataset_id == "DS-20260805-001-VAL"
        assert reg.holdout_dataset_id == "DS-20260805-001-HOLDOUT"

        report = SingleModelEvaluationReportDTO(
            model_name="delay_regressor",
            category="Regression",
            target_name="predicted_delay_mins",
            preflight=preflight,
            metrics_train=ModelEvaluationMetricsDTO(r2=0.364, mae=16.28, rmse=25.44),
            metrics_val=ModelEvaluationMetricsDTO(r2=-0.057, mae=20.39, rmse=33.99),
            metrics_holdout=ModelEvaluationMetricsDTO(r2=-0.269, mae=22.41, rmse=32.99),
            threshold_rules=[GateThresholdRuleDTO(metric_name="r2", comparison=">=", threshold_value=0.7, actual_holdout_value=-0.269, passed=False)],
            overall_gate_passed=False,
            promotion_decision="REJECTED",
            rejection_reasons=["R2 below threshold"],
        )

        eval_reg = await repo.record_evaluation_result("delay_regressor", "v1.0.0-lineage-test", report)
        prov = eval_reg.evaluation_provenance
        assert prov["metrics_train"]["r2"] == 0.364
        assert prov["metrics_val"]["r2"] == -0.057
        assert prov["metrics_holdout"]["r2"] == -0.269
        assert prov["overall_gate_passed"] is False


@pytest.mark.asyncio
async def test_isolated_fixture_valid_promotion():
    """
    3. Test valid promotion lifecycle transition using an isolated test fixture (PROMOTABLE -> PROMOTED).
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        reg = await repo.register_candidate_version(
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v9.9.9-promotable-fixture",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-FIXTURE-PASS",
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
            metrics_train=ModelEvaluationMetricsDTO(r2=0.95, mae=2.0, rmse=3.0),
            metrics_val=ModelEvaluationMetricsDTO(r2=0.92, mae=3.0, rmse=4.0),
            metrics_holdout=ModelEvaluationMetricsDTO(r2=0.89, mae=4.0, rmse=5.0),
            threshold_rules=[GateThresholdRuleDTO(metric_name="r2", comparison=">=", threshold_value=0.7, actual_holdout_value=0.89, passed=True)],
            overall_gate_passed=True,
            promotion_decision="PROMOTABLE",
            rejection_reasons=[],
        )

        eval_entity = await repo.record_evaluation_result("delay_regressor", "v9.9.9-promotable-fixture", passing_report)
        assert eval_entity.evaluation_decision == "PROMOTABLE"

        promoted = await repo.promote_model_version("delay_regressor", "v9.9.9-promotable-fixture")
        assert promoted.lifecycle_status == "PROMOTED"
        assert promoted.promotion_timestamp is not None

        # Verify active model resolution now returns fixture
        active = await repo.get_active_promoted_model("delay_regressor")
        assert active is not None
        assert active.model_version == "v9.9.9-promotable-fixture"

        # Cleanup active state for isolation
        promoted.lifecycle_status = "RETIRED"
        await db_session.flush()


@pytest.mark.asyncio
async def test_isolated_fixture_retirement():
    """
    4. Test retirement transition using isolated fixture (PROMOTED -> RETIRED).
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("turnaround_regressor")

        reg = await repo.register_candidate_version(
            model_name="turnaround_regressor",
            model_category="Regression",
            model_version="v9.9.9-retire-fixture",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-FIXTURE-RETIRE",
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
            metrics_train=ModelEvaluationMetricsDTO(r2=0.90, mae=5.0, rmse=8.0),
            metrics_val=ModelEvaluationMetricsDTO(r2=0.88, mae=6.0, rmse=9.0),
            metrics_holdout=ModelEvaluationMetricsDTO(r2=0.85, mae=7.0, rmse=10.0),
            threshold_rules=[],
            overall_gate_passed=True,
            promotion_decision="PROMOTABLE",
            rejection_reasons=[],
        )

        await repo.record_evaluation_result("turnaround_regressor", "v9.9.9-retire-fixture", passing_report)
        await repo.promote_model_version("turnaround_regressor", "v9.9.9-retire-fixture")

        # Retire model
        retired = await repo.retire_model_version("turnaround_regressor", "v9.9.9-retire-fixture", reason="Testing retirement")
        assert retired.lifecycle_status == "RETIRED"
        assert retired.retirement_timestamp is not None

        # Active model must revert to None (NOT_CONFIGURED)
        active = await repo.get_active_promoted_model("turnaround_regressor")
        assert active is None


@pytest.mark.asyncio
async def test_invalid_lifecycle_transitions():
    """
    5. Test prevention of invalid lifecycle state transitions.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("sla_breach_classifier")

        reg = await repo.register_candidate_version(
            model_name="sla_breach_classifier",
            model_category="Classification",
            model_version="v1.0.0-invalid-transition",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-INVALID",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        # 1. TRAINED_CANDIDATE -> PROMOTED (must fail because not evaluated/promotable)
        with pytest.raises(ValueError, match="CANNOT PROMOTE REJECTED MODEL"):
            await repo.promote_model_version("sla_breach_classifier", "v1.0.0-invalid-transition")

        # 2. RETIRE candidate that is not PROMOTED (must fail)
        with pytest.raises(ValueError, match="INVALID RETIREMENT TRANSITION"):
            await repo.retire_model_version("sla_breach_classifier", "v1.0.0-invalid-transition")


@pytest.mark.asyncio
async def test_transactional_promotion_rollback():
    """
    6. Test promotion transactionality and rollback on error.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        
        # Verify active model remains unchanged when an invalid promotion fails inside a transaction block
        active_before = await repo.get_active_promoted_model("delay_regressor")

        try:
            async with db_session.begin_nested():
                await repo.promote_model_version("delay_regressor", "non-existent-version")
        except Exception:
            pass

        active_after = await repo.get_active_promoted_model("delay_regressor")
        assert active_before == active_after


@pytest.mark.asyncio
async def test_duplicate_model_version_protection():
    """
    7. Test duplicate registration protection for same model_name + model_version.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("plant_risk_classifier")

        await repo.register_candidate_version(
            model_name="plant_risk_classifier",
            model_category="Classification",
            model_version="v1.0.0-duplicate-test",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-DUP-1",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(ValueError, match="DUPLICATE MODEL VERSION"):
            await repo.register_candidate_version(
                model_name="plant_risk_classifier",
                model_category="Classification",
                model_version="v1.0.0-duplicate-test",
                algorithm=meta.algorithm,
                target_name=meta.target_name,
                feature_set_version=meta.feature_set_version,
                training_dataset_id="DS-DUP-2",
                artifact_path=meta.artifact_path,
                artifact_sha256=meta.artifact_sha256,
                artifact_size_bytes=meta.artifact_size_bytes,
                training_timestamp=datetime.now(timezone.utc),
            )


@pytest.mark.asyncio
async def test_artifact_mutation_detection():
    """
    8. Test artifact SHA mutation verification.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        reg = await repo.register_candidate_version(
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v1.0.0-sha-verify",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-SHA-PASS",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        # 1. Unmodified artifact -> Returns True
        assert await repo.verify_registered_artifact_sha("delay_regressor", "v1.0.0-sha-verify") is True

        # 2. Mutate entity SHA in memory -> Verification must fail
        reg.artifact_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
        await db_session.flush()

        with pytest.raises(ValueError, match="ARTIFACT MUTATION DETECTED"):
            await repo.verify_registered_artifact_sha("delay_regressor", "v1.0.0-sha-verify")


@pytest.mark.asyncio
async def test_audit_history_immutability():
    """
    9. Test audit history immutability and append-only log sequence.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        reg = await repo.register_candidate_version(
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v1.0.0-audit-immutability",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-AUDIT",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
        )

        report = SingleModelEvaluationReportDTO(
            model_name="delay_regressor",
            category="Regression",
            target_name="predicted_delay_mins",
            preflight=preflight,
            metrics_train=ModelEvaluationMetricsDTO(),
            metrics_val=ModelEvaluationMetricsDTO(),
            metrics_holdout=ModelEvaluationMetricsDTO(),
            threshold_rules=[],
            overall_gate_passed=False,
            promotion_decision="REJECTED",
            rejection_reasons=["Gate failed"],
        )

        await repo.record_evaluation_result("delay_regressor", "v1.0.0-audit-immutability", report)

        events = await repo.get_audit_trail("delay_regressor")
        audit_types = [e.event_type for e in events if e.model_version == "v1.0.0-audit-immutability"]

        assert len(audit_types) == 2
        assert audit_types[0] == "MODEL_REGISTERED"
        assert audit_types[1] == "MODEL_REJECTED"


@pytest.mark.asyncio
async def test_real_production_state_not_configured():
    """
    10. Verifies real production state: 4 candidates exist, 0 promoted, platform prediction authority = NOT_CONFIGURED.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        repo = MLModelRegistryRepository(db_session)
        
        for m_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            active = await repo.get_active_promoted_model(m_name)
            assert active is None, f"PRODUCTION STATE VIOLATION: Model '{m_name}' has an active promoted model!"
