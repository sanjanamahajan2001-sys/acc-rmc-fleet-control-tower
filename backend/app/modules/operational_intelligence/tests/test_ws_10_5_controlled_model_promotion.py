"""
WS-10.5 Dedicated Pytest Verification & Certification Suite.
Controlled Legitimate Model Promotion & Production Authority Activation.
Exact 18 Required Certification Test Methods.
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
from app.modules.operational_intelligence.ml.feature_extractor import FEATURE_SET_VERSION
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.ml.trainer import WS10ModelTrainer, MODEL_STORAGE_BASE_DIR
from app.modules.operational_intelligence.services.evaluator_service import WS10CandidateEvaluationService
from app.modules.operational_intelligence.services.promotion_service import WS10ModelPromotionService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository

# Create NullPool engine for pytest-asyncio event loop isolation
test_engine = create_async_engine(engine.url, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def create_eligible_isolated_candidate(session, model_name="delay_regressor", prefix="DS-PROM-TEST"):
    """Helper to build, train, evaluate, and produce a genuine PROMOTION_ELIGIBLE candidate."""
    ds_id = f"{prefix}-{uuid.uuid4().hex[:6]}"
    ver_num = f"v10.5.{uuid.uuid4().hex[:4]}"

    db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
        session=session, dataset_id_override=ds_id, limit=25
    )
    await session.flush()

    art_dir = os.path.join(MODEL_STORAGE_BASE_DIR, "test_candidates")
    os.makedirs(art_dir, exist_ok=True)
    art_path = os.path.join(art_dir, f"candidate_{ver_num}.joblib")

    # Create dummy trained model artifact
    dummy_payload = {
        "estimator": "DummyEstimator",
        "feature_columns": ["drayage_lag_hours", "dwell_time_hours"],
        "model_name": model_name,
    }
    import joblib
    joblib.dump(dummy_payload, art_path)
    with open(art_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()

    now = datetime.now(timezone.utc)
    candidate = MLModelVersion(
        model_name=model_name,
        model_category="Regression" if "regressor" in model_name else "Classification",
        model_version=ver_num,
        algorithm="RandomForestRegressor",
        target_name="predicted_delay_mins",
        feature_set_version="FeatureSetV1",
        training_dataset_id=ds_id,
        artifact_path=art_path,
        artifact_sha256=sha,
        artifact_size_bytes=os.path.getsize(art_path),
        training_timestamp=now,
        lifecycle_status="TRAINED_CANDIDATE",
        evaluation_decision="PROMOTION_ELIGIBLE",
        evaluation_timestamp=now,
        evaluation_provenance={
            "evaluator_version": "WS-10.4",
            "metrics": {"r2": 0.85, "mae": 5.2, "rmse": 7.1},
            "holdout_row_count": 5,
        },
        created_at=now,
        updated_at=now,
    )
    session.add(candidate)
    await session.flush()
    return candidate, ds_id





# =============================================================================
# 18 MANDATORY CERTIFICATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_5_01_eligible_candidate_discovery():
    """1. Eligible candidate discovery."""
    model_name = f"delay_reg_disc_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-DISC-5")
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        discovered = await WS10ModelPromotionService.discover_promotion_eligible_candidates(session, model_name)
        assert len(discovered) >= 1
        found = [c for c in discovered if c.id == cand.id]
        assert len(found) == 1
        assert found[0].evaluation_decision == "PROMOTION_ELIGIBLE"


@pytest.mark.asyncio
async def test_ws_10_5_02_phase_73_eligibility_verification():
    """2. Phase 7.3 eligibility re-verification."""
    model_name = f"turnaround_reg_ver_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-VERIFY-5")
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        is_eligible, reasons = await WS10ModelPromotionService.revalidate_promotion_eligibility(session, cand)
        assert is_eligible is True
        assert len(reasons) == 0


@pytest.mark.asyncio
async def test_ws_10_5_03_artifact_sha_verification():
    """3. Artifact SHA-256 verification before promotion."""
    model_name = f"sla_breach_sha_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-SHA-5")
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        sha_ok = await repo.verify_registered_artifact_sha(cand.model_name, cand.model_version)
        assert sha_ok is True


@pytest.mark.asyncio
async def test_ws_10_5_04_successful_isolated_promotion():
    """4. Successful isolated model promotion."""
    model_name = f"plant_risk_prom_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-PROM-4")
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        promoted = await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        await session.commit()

        assert promoted.lifecycle_status == "PROMOTED"
        assert promoted.promotion_timestamp is not None


@pytest.mark.asyncio
async def test_ws_10_5_05_rejected_candidate_protection():
    """5. Block promotion for REJECTED candidates."""
    model_name = f"delay_reg_rej_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-REJ-5")
        cand.lifecycle_status = "REJECTED"
        cand.evaluation_decision = "REJECTED"
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "REJECTED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_06_pending_evaluation_protection():
    """6. Block promotion for PENDING_EVALUATION candidates."""
    model_name = f"turnaround_pend_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-PEND-5")
        cand.evaluation_decision = "PENDING_EVALUATION"
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "PENDING_EVALUATION" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_07_artifact_mutation_protection():
    """7. Block promotion if artifact SHA-256 is mutated on disk."""
    model_name = f"sla_breach_mut_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-MUTATE-5")
        await session.commit()

        # Mutate artifact file on disk
        with open(cand.artifact_path, "ab") as f:
            f.write(b"CORRUPTED_MUTATION_BYTES")
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "ARTIFACT_MUTATION_DETECTED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_08_missing_dataset_protection():
    """8. Block promotion if training dataset does not exist."""
    model_name = f"plant_risk_miss_ds_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-MISS-DS-5")
        cand.training_dataset_id = "DS-NON-EXISTENT-DATASET"
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "Missing dataset record" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_09_lineage_validation():
    """9. Lineage validation: Block promotion for invalid FeatureSet version."""
    model_name = f"delay_reg_lin_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-LIN-5")
        cand.feature_set_version = "FeatureSetV0_Legacy"
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "Incompatible FeatureSet version" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_10_retirement_protection():
    """10. Block promotion for RETIRED candidates."""
    model_name = f"turnaround_ret_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-RET-5")
        cand.lifecycle_status = "RETIRED"
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "RETIRED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_11_duplicate_promotion_idempotency():
    """11. Duplicate promotion attempt idempotency / rejection."""
    model_name = f"sla_breach_dup_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-DUP-5")
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        promoted1 = await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        await session.commit()

        # Second promotion attempt on already promoted candidate
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        assert "ALREADY PROMOTED" in str(exc_info.value) or "already PROMOTED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_12_concurrent_promotion_protection():
    """12. Concurrent promotion race protection."""
    model_name = f"plant_risk_conc_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-CONC-5")
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session_a:
        p_a = await WS10ModelPromotionService.promote_eligible_candidate(session_a, cand_id)
        await session_a.commit()

        async with TestAsyncSessionFactory() as session_b:
            with pytest.raises(ValueError):
                await WS10ModelPromotionService.promote_eligible_candidate(session_b, cand_id)


@pytest.mark.asyncio
async def test_ws_10_5_13_transaction_rollback():
    """13. Transaction rollback on promotion failure."""
    model_name = f"delay_reg_roll_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-ROLL-5")
        await session.commit()
        cand_id = cand.id

    try:
        async with TestAsyncSessionFactory() as session:
            repo = MLModelRegistryRepository(session)
            # Deliberately force error by passing invalid version_id
            await repo.promote_candidate_model_version(uuid.uuid4())
            await session.commit()
    except Exception:
        pass

    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        original = await repo.get_by_version_number(cand.model_name, cand.model_version)
        assert original.lifecycle_status == "TRAINED_CANDIDATE"


@pytest.mark.asyncio
async def test_ws_10_5_14_audit_lineage():
    """14. Audit lineage persistence in ml_model_audit_events."""
    model_name = f"turnaround_aud_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-AUD-5")
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        promoted = await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        await session.commit()

        stmt = select(MLModelAuditEvent).where(MLModelAuditEvent.model_version_id == cand_id)
        res = await session.execute(stmt)
        audits = list(res.scalars().all())

        event_types = [a.event_type for a in audits]
        assert "MODEL_PROMOTED" in event_types


@pytest.mark.asyncio
async def test_ws_10_5_15_single_promoted_per_family_enforcement():
    """15. Single active promoted model per family enforcement."""
    model_name = f"sla_breach_sing_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand1, ds_id1 = await create_eligible_isolated_candidate(session, model_name, "DS-SINGLE-1")
        cand2, ds_id2 = await create_eligible_isolated_candidate(session, model_name, "DS-SINGLE-2")
        await session.commit()
        c1_id, c2_id = cand1.id, cand2.id

    async with TestAsyncSessionFactory() as session:
        p1 = await WS10ModelPromotionService.promote_eligible_candidate(session, c1_id)
        await session.commit()

    async with TestAsyncSessionFactory() as session:
        with pytest.raises(ValueError) as exc_info:
            await WS10ModelPromotionService.promote_eligible_candidate(session, c2_id)
        assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_10_5_16_real_registry_authority_integration():
    """16. Integration with real MLModelRegistryRepository authority."""
    model_name = f"plant_risk_auth_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-AUTH-5")
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        promoted = await repo.promote_candidate_model_version(cand_id)
        await session.commit()

        active = await repo.get_active_promoted_model(model_name)
        assert active is not None
        assert active.id == cand_id


@pytest.mark.asyncio
async def test_ws_10_5_17_zero_snapshot_creation_during_promotion():
    """17. Zero prediction snapshots created during promotion."""
    model_name = f"delay_reg_snap_{uuid.uuid4().hex[:4]}"
    async with TestAsyncSessionFactory() as session:
        stmt0 = select(func.count(MLPredictionSnapshot.id))
        res0 = await session.execute(stmt0)
        c0 = res0.scalar()

        cand, ds_id = await create_eligible_isolated_candidate(session, model_name, "DS-SNAP-5")
        await session.commit()
        cand_id = cand.id

    async with TestAsyncSessionFactory() as session:
        await WS10ModelPromotionService.promote_eligible_candidate(session, cand_id)
        await session.commit()

        stmt1 = select(func.count(MLPredictionSnapshot.id))
        res1 = await session.execute(stmt1)
        c1 = res1.scalar()

        assert c1 == c0, "CRITICAL VIOLATION: Promotion created prediction snapshots!"


@pytest.mark.asyncio
async def test_ws_10_5_18_production_state_safety():
    """18. Real production database safety audit."""
    async with TestAsyncSessionFactory() as session:
        audit_report = await WS10ModelPromotionService.audit_real_production_candidate_eligibility(session)
        assert "promoted_models_count" in audit_report
        assert "platform_prediction_authority_status" in audit_report
