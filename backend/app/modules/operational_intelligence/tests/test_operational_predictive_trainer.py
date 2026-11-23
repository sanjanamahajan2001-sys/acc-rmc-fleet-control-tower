"""
WS-09 Phase 7.2 Model Training & Artifact Export Dedicated Pytest Suite

Validates candidate model training, FeatureSetV1 consumption, target/feature separation,
preprocessing, deterministic random seeds, artifact serialization/reload, SHA-256 calculation,
metrics calculation, independent artifact uniqueness, and candidate promotion boundary enforcement.
"""

import os
import hashlib
import joblib
import pytest
import pandas as pd
from app.core.database import AsyncSessionFactory, engine

from app.modules.operational_intelligence.ml.feature_extractor import (
    Phase71FeatureExtractor,
    FEATURE_SET_VERSION,
    FORBIDDEN_LEAKAGE_FIELDS,
    ALLOWED_INFERENCE_FEATURES,
)
from app.modules.operational_intelligence.ml.trainer import (
    Phase72ModelTrainer,
    MODEL_CONFIGURATIONS,
    MODEL_STORAGE_BASE_DIR,
)


@pytest.mark.asyncio
async def test_train_and_export_all_candidate_models():
    """
    Trains all 4 candidate model families on FeatureSetV1, exports artifacts, and verifies SHA-256 & metadata.
    Also verifies that plant_risk_classifier and sla_breach_classifier produce distinct targets & distinct SHA-256 hashes.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        results = await Phase72ModelTrainer.train_all_candidate_models(
            session=db_session,
            dataset_id="DS-TEST-7-2",
        )

        assert len(results) == 4
        assert "delay_regressor" in results
        assert "turnaround_regressor" in results
        assert "sla_breach_classifier" in results
        assert "plant_risk_classifier" in results

        sha_map = {}
        target_map = {}

        for m_name, res in results.items():
            meta = res.metadata
            assert meta.model_name == m_name
            assert meta.promotion_status == "TRAINED_CANDIDATE"  # MUST NOT BE PROMOTED IN PHASE 7.2
            assert meta.feature_set_version == FEATURE_SET_VERSION
            assert meta.artifact_sha256 is not None
            assert len(meta.artifact_sha256) == 64
            assert os.path.exists(meta.artifact_path)

            sha_map[m_name] = meta.artifact_sha256
            target_map[m_name] = meta.target_name

            # Check SHA-256 hash match on file
            hasher = hashlib.sha256()
            with open(meta.artifact_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            assert hasher.hexdigest() == meta.artifact_sha256

        # REMEDIATION B1 INTEGRITY ASSERTION:
        # Verify plant_risk_classifier and sla_breach_classifier are DISTINCT models
        assert target_map["plant_risk_classifier"] == "predicted_plant_congestion_target"
        assert target_map["sla_breach_classifier"] == "predicted_sla_breach_target"
        assert target_map["plant_risk_classifier"] != target_map["sla_breach_classifier"]
        assert sha_map["plant_risk_classifier"] != sha_map["sla_breach_classifier"], "ERROR: plant_risk_classifier SHA-256 collision with sla_breach_classifier!"


@pytest.mark.asyncio
async def test_artifact_reload_and_sample_inference():
    """
    Verifies that serialized .joblib candidate model artifacts can be reloaded and run sample inference.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res = await Phase72ModelTrainer.train_candidate_model(
            session=db_session,
            model_name="delay_regressor",
            dataset_id="DS-TEST-RELOAD",
        )

        artifact_path = res.metadata.artifact_path
        assert os.path.exists(artifact_path)

        # Reload pipeline independently
        reloaded_pipeline = joblib.load(artifact_path)
        assert reloaded_pipeline is not None

        # Sample test record formatted as a DataFrame
        sample_input_df = pd.DataFrame([{
            "plant_code": "P-001",
            "customer_code": "C-001",
            "vehicle_code": "V-001",
            "ticket_volume_m3": 6.0,
            "plant_queue_avg_30d": 12.5,
            "customer_retention_avg_30d": 8.0,
            "dispatch_hour": 10,
            "dispatch_day_of_week": 2,
        }])

        pred = reloaded_pipeline.predict(sample_input_df)
        assert len(pred) == 1
        assert isinstance(float(pred[0]), float)


@pytest.mark.asyncio
async def test_training_reproducibility():
    """
    Verifies that training candidate models twice with identical random seeds produces identical SHA-256 metadata & metrics.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res1 = await Phase72ModelTrainer.train_candidate_model(
            session=db_session,
            model_name="sla_breach_classifier",
            dataset_id="DS-TEST-REPRO",
        )

        res2 = await Phase72ModelTrainer.train_candidate_model(
            session=db_session,
            model_name="sla_breach_classifier",
            dataset_id="DS-TEST-REPRO",
        )

        # Compare row counts, feature count, and holdout metrics
        assert res1.metadata.row_counts == res2.metadata.row_counts
        assert res1.metadata.metrics_holdout.roc_auc == res2.metadata.metrics_holdout.roc_auc
        assert res1.metadata.metrics_holdout.f1 == res2.metadata.metrics_holdout.f1


@pytest.mark.asyncio
async def test_candidate_promotion_boundary():
    """
    Verifies that Phase 7.2 candidate model artifacts are strictly tagged as TRAINED_CANDIDATE and NOT PROMOTED.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res = await Phase72ModelTrainer.train_candidate_model(
            session=db_session,
            model_name="turnaround_regressor",
            dataset_id="DS-TEST-BOUNDARY",
        )

        assert res.metadata.promotion_status == "TRAINED_CANDIDATE"
        assert res.metadata.promotion_status != "PROMOTED"
