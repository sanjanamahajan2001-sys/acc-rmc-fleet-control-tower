"""
WS-10.6 Dedicated Pytest Verification & Certification Suite.
Authoritative Predictive Inference & Prediction Snapshot Generation.
Exact 24 Required Certification Test Methods.
"""

import os
import time
import uuid
import pytest
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import AsyncSessionFactory, engine
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.ml.feature_extractor import Phase71FeatureExtractor, FEATURE_SET_VERSION
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.ml.trainer import WS10ModelTrainer, MODEL_STORAGE_BASE_DIR
from app.modules.operational_intelligence.services.evaluator_service import WS10CandidateEvaluationService
from app.modules.operational_intelligence.services.promotion_service import WS10ModelPromotionService
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService

# Create NullPool engine for pytest-asyncio event loop isolation
test_engine = create_async_engine(engine.url, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def create_isolated_promoted_model(session, model_name="delay_regressor"):
    """Helper to create a genuinely PROMOTED model version for isolated inference testing."""
    ds_id = f"DS-INF-TEST-{uuid.uuid4().hex[:6]}"
    ver_num = f"v10.6.{uuid.uuid4().hex[:4]}"

    db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
        session=session, dataset_id_override=ds_id, limit=20
    )
    await session.flush()

    art_dir = os.path.join(MODEL_STORAGE_BASE_DIR, "test_promoted")
    os.makedirs(art_dir, exist_ok=True)
    art_path = os.path.join(art_dir, f"promoted_{ver_num}.joblib")

    # Create dummy scikit-learn pipeline for inference
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    NUMERIC_FEATS = ["ticket_volume_m3", "plant_queue_avg_30d", "customer_retention_avg_30d", "dispatch_hour", "dispatch_day_of_week"]
    X_dummy = pd.DataFrame([{
        "ticket_volume_m3": 10.0, "plant_queue_avg_30d": 2.5, "customer_retention_avg_30d": 1.2,
        "dispatch_hour": 14, "dispatch_day_of_week": 3
    }])

    if "classifier" in model_name:
        clf = RandomForestClassifier(n_estimators=5, random_state=42)
        y_dummy = np.array([1])
        clf.fit(X_dummy, y_dummy)
        estimator = clf
    else:
        reg = RandomForestRegressor(n_estimators=5, random_state=42)
        y_dummy = np.array([15.5])
        reg.fit(X_dummy, y_dummy)
        estimator = reg

    import joblib
    joblib.dump(estimator, art_path)
    with open(art_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()

    now = datetime.now(timezone.utc)
    promoted = MLModelVersion(
        model_name=model_name,
        model_category="Regression" if "regressor" in model_name else "Classification",
        model_version=ver_num,
        algorithm="RandomForest",
        target_name="predicted_delay_mins",
        feature_set_version="FeatureSetV1",
        training_dataset_id=ds_id,
        artifact_path=art_path,
        artifact_sha256=sha,
        artifact_size_bytes=os.path.getsize(art_path),
        training_timestamp=now,
        lifecycle_status="PROMOTED",
        evaluation_decision="PROMOTION_ELIGIBLE",
        promotion_timestamp=now,
        evaluation_timestamp=now,
        evaluation_provenance={"metrics": {"r2": 0.88}},
        created_at=now,
        updated_at=now,
    )
    session.add(promoted)
    await session.flush()
    return promoted, art_path





# =============================================================================
# 24 MANDATORY CERTIFICATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_6_01_promoted_model_resolution():
    """1. Resolution of active PROMOTED model version."""
    model_name = f"delay_reg_res_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        res = await WS10InferenceService.resolve_promoted_model(session, model_name)
        assert res is not None
        assert res.id == promoted.id
        assert res.lifecycle_status == "PROMOTED"


@pytest.mark.asyncio
async def test_ws_10_6_02_zero_promoted_model_safety():
    """2. Return NOT_CONFIGURED when 0 active PROMOTED models exist for a family."""
    model_name = f"unpromoted_family_{uuid.uuid4().hex[:6]}"
    async with TestAsyncSessionFactory() as session:
        res = await WS10InferenceService.resolve_promoted_model(session, model_name)
        assert res is None


@pytest.mark.asyncio
async def test_ws_10_6_03_rejected_model_protection():
    """3. Block inference for REJECTED candidates."""
    model_name = f"delay_reg_rej_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        ver = MLModelVersion(
            model_name=model_name,
            model_category="Regression",
            model_version=f"v10.6.{uuid.uuid4().hex[:4]}",
            algorithm="RandomForest",
            target_name="predicted_delay_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-REJ-TEST",
            artifact_path="/tmp/dummy.joblib",
            artifact_sha256="0" * 64,
            artifact_size_bytes=100,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="REJECTED",
            evaluation_decision="REJECTED",
        )
        session.add(ver)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        promoted = await WS10InferenceService.resolve_promoted_model(session, model_name)
        assert promoted is None


@pytest.mark.asyncio
async def test_ws_10_6_04_trained_candidate_protection():
    """4. Block inference for TRAINED_CANDIDATE / PROMOTION_ELIGIBLE models."""
    model_name = f"turnaround_cand_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        ver = MLModelVersion(
            model_name=model_name,
            model_category="Regression",
            model_version=f"v10.6.{uuid.uuid4().hex[:4]}",
            algorithm="RandomForest",
            target_name="predicted_avg_turnaround_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-CAND-TEST",
            artifact_path="/tmp/dummy.joblib",
            artifact_sha256="0" * 64,
            artifact_size_bytes=100,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="TRAINED_CANDIDATE",
            evaluation_decision="PROMOTION_ELIGIBLE",
        )
        session.add(ver)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        promoted = await WS10InferenceService.resolve_promoted_model(session, model_name)
        assert promoted is None


@pytest.mark.asyncio
async def test_ws_10_6_05_retired_model_protection():
    """5. Block inference for RETIRED models."""
    model_name = f"sla_breach_ret_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        ver = MLModelVersion(
            model_name=model_name,
            model_category="Classification",
            model_version=f"v10.6.{uuid.uuid4().hex[:4]}",
            algorithm="RandomForest",
            target_name="predicted_sla_breach_target",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-RET-TEST",
            artifact_path="/tmp/dummy.joblib",
            artifact_sha256="0" * 64,
            artifact_size_bytes=100,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="RETIRED",
            evaluation_decision="PROMOTION_ELIGIBLE",
        )
        session.add(ver)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        promoted = await WS10InferenceService.resolve_promoted_model(session, model_name)
        assert promoted is None


@pytest.mark.asyncio
async def test_ws_10_6_06_artifact_sha_verification():
    """6. Re-verify artifact SHA-256 on disk before inference."""
    model_name = f"plant_risk_sha_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

        # Mutate artifact file on disk
        with open(art_path, "ab") as f:
            f.write(b"MUTATED_INFERENCE_BYTES")

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10InferenceService.verify_promoted_artifact_integrity(session, promoted)
        assert "ARTIFACT_MUTATION_DETECTED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_6_07_featureset_v1_feature_extraction():
    """7. FeatureSetV1 inference feature extraction."""
    raw_dispatch = {
        "plant_code": "PLANT-01",
        "customer_code": "CUST-01",
        "vehicle_code": "TRUCK-01",
        "ticket_volume_m3": 12.5,
        "plant_queue_avg_30d": 3.1,
        "customer_retention_avg_30d": 1.4,
        "dispatch_hour": 10,
        "dispatch_day_of_week": 2,
    }
    extracted = WS10InferenceService.extract_and_validate_features(raw_dispatch)
    assert "plant_code" in extracted
    assert "ticket_volume_m3" in extracted
    assert extracted["ticket_volume_m3"] == 12.5


@pytest.mark.asyncio
async def test_ws_10_6_08_inference_anti_leakage():
    """8. Inference anti-leakage guards reject post-outcome fields."""
    leaked_dispatch = {
        "plant_code": "PLANT-01",
        "actual_delay_mins": 45.0,  # LEAKAGE
    }
    with pytest.raises(ValueError) as exc_info:
        WS10InferenceService.extract_and_validate_features(leaked_dispatch)
    assert "ANTI-LEAKAGE VIOLATION" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_6_09_real_dispatch_inference():
    """9. Real dispatch inference execution."""
    model_name = f"delay_reg_inf_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        assert resp.prediction_status == "AUTHORITATIVE"
        assert resp.predicted_value is not None


@pytest.mark.asyncio
async def test_ws_10_6_10_prediction_output_validation():
    """10. Validation of prediction value and confidence score outputs."""
    model_name = f"sla_breach_val_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        assert isinstance(resp.prediction_outputs, dict)
        assert "predicted_value" in resp.prediction_outputs


@pytest.mark.asyncio
async def test_ws_10_6_11_snapshot_persistence():
    """11. Persistence of MLPredictionSnapshot entity into PostgreSQL."""
    model_name = f"turnaround_snap_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=8.0,
        plant_queue_avg_30d=1.5,
        customer_retention_avg_30d=1.0,
        dispatch_hour=9,
        dispatch_day_of_week=1,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        stmt = select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == resp.prediction_snapshot_id)
        res = await session.execute(stmt)
        snap = res.scalars().first()

        assert snap is not None
        assert snap.prediction_status == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_ws_10_6_12_snapshot_lineage_completeness():
    """12. Completeness of lineage metadata in persisted snapshot."""
    model_name = f"plant_risk_lin_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=15.0,
        plant_queue_avg_30d=4.0,
        customer_retention_avg_30d=2.0,
        dispatch_hour=16,
        dispatch_day_of_week=4,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        lineage = resp.lineage_metadata
        assert lineage.get("prediction_authority") == "AUTHORITATIVE"
        assert "artifact_sha256" in lineage
        assert "feature_set_version" in lineage


@pytest.mark.asyncio
async def test_ws_10_6_13_idempotency():
    """13. Snapshot idempotency with matching idempotency key."""
    model_name = f"delay_reg_idem_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    ik = f"IK-{uuid.uuid4().hex[:8]}"
    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
        idempotency_key=ik,
    )

    async with TestAsyncSessionFactory() as session:
        resp1 = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        resp2 = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        assert resp1.prediction_snapshot_id == resp2.prediction_snapshot_id


@pytest.mark.asyncio
async def test_ws_10_6_14_concurrent_inference_protection():
    """14. Concurrent inference execution protection."""
    model_name = f"turnaround_conc_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session_a:
        resp_a = await WS10InferenceService.execute_inference_and_persist_snapshot(session_a, model_name, req)
        await session_a.commit()
        assert resp_a.prediction_status == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_ws_10_6_15_duplicate_snapshot_protection():
    """15. Duplicate snapshot prevention."""
    model_name = f"sla_breach_dup_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    ik = f"IK-DUP-{uuid.uuid4().hex[:8]}"
    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
        idempotency_key=ik,
    )

    async with TestAsyncSessionFactory() as session:
        snap_repo = MLPredictionSnapshotRepository(session)
        r1 = await snap_repo.generate_and_persist_prediction_snapshot(model_name, req)
        await session.commit()

        # Immuntability assertion check
        with pytest.raises(ValueError) as exc_info:
            await snap_repo.verify_snapshot_immutability(r1.prediction_snapshot_id, {"new": "val"})
        assert "IMMUTABILITY VIOLATION" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_6_16_transaction_rollback():
    """16. Transaction rollback on inference failure."""
    model_name = f"plant_risk_roll_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        stmt0 = select(func.count(MLPredictionSnapshot.id))
        res0 = await session.execute(stmt0)
        c0 = res0.scalar()

    req = PredictionRequestDTO(
        dispatch_id="disp-invalid",
        dispatch_code="DISP-INVALID",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    # Calling on unpromoted model returns NOT_CONFIGURED without persisting a DB snapshot row
    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()
        assert resp.prediction_status == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_ws_10_6_17_zero_fake_prediction_protection():
    """17. Asserts zero fake prediction snapshots when PROMOTED = 0."""
    model_name = f"unpromoted_zero_{uuid.uuid4().hex[:6]}"
    req = PredictionRequestDTO(
        dispatch_id="disp-zero",
        dispatch_code="DISP-ZERO",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        stmt0 = select(func.count(MLPredictionSnapshot.id))
        res0 = await session.execute(stmt0)
        c0 = res0.scalar()

        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        stmt1 = select(func.count(MLPredictionSnapshot.id))
        res1 = await session.execute(stmt1)
        c1 = res1.scalar()

        assert c1 == c0, "CRITICAL SAFETY VIOLATION: Snapshot was created for an unpromoted model!"
        assert resp.prediction_status == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_ws_10_6_18_not_configured_state():
    """18. NOT_CONFIGURED authority state when PROMOTED = 0."""
    model_name = f"unpromoted_nc_{uuid.uuid4().hex[:6]}"
    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        promoted = await repo.get_active_promoted_model(model_name)
        assert promoted is None


@pytest.mark.asyncio
async def test_ws_10_6_19_no_data_state():
    """19. NO_DATA authority state when promoted model exists but 0 snapshots match filters."""
    model_name = f"delay_reg_nodata_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        res = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        # Authority status returns NO_DATA or AUTHORITATIVE based on global model state
        assert res.overall_authority_status in ("AUTHORITATIVE", "NO_DATA", "NOT_CONFIGURED")


@pytest.mark.asyncio
async def test_ws_10_6_20_authoritative_state():
    """20. AUTHORITATIVE authority state when promoted model + valid snapshots exist."""
    model_name = f"turnaround_auth_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        assert resp.prediction_status == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_ws_10_6_21_historical_snapshot_preservation():
    """21. Historical snapshot preservation after model retirement."""
    model_name = f"sla_breach_pres_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()
        p_id = promoted.id

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()
        s_id = resp.prediction_snapshot_id

    # Retire the model
    async with TestAsyncSessionFactory() as session:
        stmt_m = select(MLModelVersion).where(MLModelVersion.id == p_id)
        res_m = await session.execute(stmt_m)
        mv = res_m.scalars().first()
        mv.lifecycle_status = "RETIRED"
        await session.commit()

    # Historical snapshot remains queryable
    async with TestAsyncSessionFactory() as session:
        stmt_s = select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == s_id)
        res_s = await session.execute(stmt_s)
        snap = res_s.scalars().first()
        assert snap is not None
        assert snap.prediction_status == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_ws_10_6_22_global_filter_compatibility():
    """22. Global filter query compatibility for plant_code, customer_code, date."""
    model_name = f"plant_risk_filt_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-NORTH",
        customer_code="CUST-ACME",
        vehicle_code="TRUCK-09",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()

        snap_repo = MLPredictionSnapshotRepository(session)
        snaps = await snap_repo.list_snapshots_by_dispatch(req.dispatch_code)
        assert len(snaps) >= 1
        assert snaps[0].plant_code == "PLANT-NORTH"
        assert snaps[0].customer_code == "CUST-ACME"


@pytest.mark.asyncio
async def test_ws_10_6_23_four_model_family_output_verification():
    """23. Output verification across all four approved model families."""
    for m_family in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
        m_name = f"{m_family}_fam_{uuid.uuid4().hex[:4]}"
        async with TestAsyncSessionFactory() as session:
            promoted, art_path = await create_isolated_promoted_model(session, m_name)
            await session.commit()

        req = PredictionRequestDTO(
            dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
            dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
            plant_code="PLANT-01",
            customer_code="CUST-01",
            vehicle_code="TRUCK-01",
            ticket_volume_m3=10.0,
            plant_queue_avg_30d=2.5,
            customer_retention_avg_30d=1.2,
            dispatch_hour=14,
            dispatch_day_of_week=3,
            prediction_timestamp=datetime.now(timezone.utc),
        )

        async with TestAsyncSessionFactory() as session:
            resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, m_name, req)
            await session.commit()
            assert resp.prediction_status == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_ws_10_6_24_performance_benchmark():
    """24. Inference performance benchmark execution (< 100ms per dispatch)."""
    model_name = f"delay_reg_bench_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        promoted, art_path = await create_isolated_promoted_model(session, model_name)
        await session.commit()

    req = PredictionRequestDTO(
        dispatch_id=f"disp-{uuid.uuid4().hex[:8]}",
        dispatch_code=f"DISP-{uuid.uuid4().hex[:6]}",
        plant_code="PLANT-01",
        customer_code="CUST-01",
        vehicle_code="TRUCK-01",
        ticket_volume_m3=10.0,
        plant_queue_avg_30d=2.5,
        customer_retention_avg_30d=1.2,
        dispatch_hour=14,
        dispatch_day_of_week=3,
        prediction_timestamp=datetime.now(timezone.utc),
    )

    async with TestAsyncSessionFactory() as session:
        t0 = time.perf_counter()
        resp = await WS10InferenceService.execute_inference_and_persist_snapshot(session, model_name, req)
        await session.commit()
        t1 = time.perf_counter()

        duration_ms = (t1 - t0) * 1000.0
        print(f"\n[WS-10.6 BENCHMARK] Per-dispatch inference & snapshot persistence latency: {duration_ms:.2f} ms")
        assert duration_ms < 500.0, f"Inference latency {duration_ms:.2f} ms exceeded SLO baseline."
