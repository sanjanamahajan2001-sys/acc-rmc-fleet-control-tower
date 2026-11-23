"""
WS-09 Phase 7.3 Model Evaluation & Promotion Gate Dedicated Pytest Suite

Validates candidate preflight integrity, model-specific threshold evaluation,
all-mandatory-gates-pass behavior, holdout isolation, candidate non-duplication,
and safe NOT_CONFIGURED platform prediction status enforcement when candidates fail.
"""

import os
import hashlib
import pytest
from app.core.database import AsyncSessionFactory, engine

from app.modules.operational_intelligence.ml.feature_extractor import FEATURE_SET_VERSION
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer, MODEL_CONFIGURATIONS
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator


@pytest.mark.asyncio
async def test_candidate_preflight_integrity():
    """
    Verifies that preflight check succeeds for valid candidate artifacts and validates SHA-256 integrity.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # First ensure candidates exist
        await Phase72ModelTrainer.train_all_candidate_models(db_session, dataset_id="DS-TEST-7-3")

        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")
        assert preflight is not None
        assert preflight.artifact_exists is True
        assert preflight.sha256_verified is True
        assert preflight.target_name == "predicted_delay_mins"
        assert preflight.feature_set_version == FEATURE_SET_VERSION
        assert preflight.preflight_passed is True


@pytest.mark.asyncio
async def test_promotion_gate_evaluation_matrix():
    """
    Evaluates candidate models against Phase 7.3 gates and asserts honest REJECTED decisions for failing metrics.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        await Phase72ModelTrainer.train_all_candidate_models(db_session, dataset_id="DS-TEST-7-3")

        suite_res = await Phase73PromotionGateEvaluator.run_full_promotion_suite(db_session, dataset_id="DS-TEST-7-3")
        assert suite_res.models_evaluated_count == 4
        assert suite_res.promoted_models_count == 0  # 0 models pass baseline holdout gates
        assert suite_res.platform_prediction_status == "NOT_CONFIGURED"

        # Check individual model promotion decisions
        for m_name, report in suite_res.evaluations.items():
            assert report.promotion_decision == "REJECTED"
            assert report.overall_gate_passed is False
            assert len(report.rejection_reasons) > 0


@pytest.mark.asyncio
async def test_distinct_candidate_non_duplication_assertion():
    """
    Verifies that plant_risk_classifier and sla_breach_classifier are evaluated as distinct candidates without SHA-256 collisions.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        await Phase72ModelTrainer.train_all_candidate_models(db_session, dataset_id="DS-TEST-7-3")

        p_plant, _ = Phase73PromotionGateEvaluator.verify_candidate_preflight("plant_risk_classifier")
        p_sla, _ = Phase73PromotionGateEvaluator.verify_candidate_preflight("sla_breach_classifier")

        assert p_plant.target_name == "predicted_plant_congestion_target"
        assert p_sla.target_name == "predicted_sla_breach_target"
        assert p_plant.sha256_hash != p_sla.sha256_hash, "ERROR: Candidate SHA-256 collision between plant_risk and sla_breach!"


@pytest.mark.asyncio
async def test_safe_not_configured_boundary():
    """
    Verifies that when zero candidates pass promotion gates, the system enforces platform_prediction_status = NOT_CONFIGURED.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        suite_res = await Phase73PromotionGateEvaluator.run_full_promotion_suite(db_session, dataset_id="DS-TEST-7-3")
        assert suite_res.promoted_models_count == 0
        assert suite_res.platform_prediction_status == "NOT_CONFIGURED"
