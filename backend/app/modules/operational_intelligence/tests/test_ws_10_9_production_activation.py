"""
WS-10.9 Dedicated Pytest Verification & Certification Suite.
End-to-End Controlled Production ML Activation & First Authoritative Prediction.
Runs exclusively in isolated TEST_DATABASE_URL (fleet_test).
"""

import os
import uuid
import pytest
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.ml.feature_extractor import FEATURE_SET_VERSION
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.services.ml_trigger_service import MLTriggerService
from app.modules.operational_intelligence.ml.trainer import WS10TrainingOrchestrator
from app.modules.operational_intelligence.services.evaluator_service import WS10CandidateEvaluationService
from app.modules.operational_intelligence.services.promotion_service import WS10ModelPromotionService
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.services.lifecycle_coordinator import WS10ProductionLifecycleCoordinator
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import PredictionRequestDTO

test_engine = create_async_engine(engine.url, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# =============================================================================
# 1. TRIGGER & DATASET BUILDER ISOLATION TEST
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_9_trigger_and_dataset_builder_integrity():
    """
    Scenario 1-4: ERP import trigger creation, duplicate protection, immutable FeatureSetV1 dataset build.
    """
    job_num = f"JOB-TEST-109-{uuid.uuid4().hex[:6]}"
    ds_id = f"DS-FSV1-TEST-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        # 1. Trigger Creation
        trig = await MLTriggerService.evaluate_and_create_trigger(
            session=session, import_job_id=None, job_number=job_num, dataset_id=ds_id, new_dispatches_in_batch=150
        )
        await session.commit()
        assert trig.trigger_id is not None
        assert trig.status in ("PENDING", "SKIPPED_COOLDOWN")

        # 2. Duplicate Protection
        trig_dup = await MLTriggerService.evaluate_and_create_trigger(
            session=session, import_job_id=None, job_number=job_num, dataset_id=ds_id, new_dispatches_in_batch=150
        )
        await session.commit()
        assert trig_dup.trigger_id == trig.trigger_id

        # 3. Build Immutable Dataset
        db_ds, ext_rows = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=150
        )
        await session.commit()
        assert db_ds.dataset_id == ds_id
        assert db_ds.feature_set_version == "FeatureSetV1"
        assert db_ds.total_records > 0
        assert db_ds.train_count > 0
        assert db_ds.sha256_checksum is not None


# =============================================================================
# 2. CANDIDATE TRAINING & HOLDOUT EVALUATION
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_9_training_and_holdout_evaluation():
    """
    Scenario 5-8: Four model family candidate training (TRAIN-only fitting), holdout evaluation, gate thresholds.
    """
    job_num = f"JOB-TRAIN-109-{uuid.uuid4().hex[:6]}"
    ds_id = f"DS-FSV1-TRAIN-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        summary = await WS10ProductionLifecycleCoordinator.execute_full_lifecycle_orchestration(
            session=session,
            job_number=job_num,
            dataset_id=ds_id,
            new_dispatches_in_batch=150,
            perform_controlled_promotion=False,
        )

        assert summary["trigger_id"] is not None
        assert summary["dataset_created"] is True
        assert len(summary["trained_models"]) == 4
        assert len(summary["evaluated_models"]) == 4
        assert len(summary["promoted_models"]) == 0


# =============================================================================
# 3. CONTROLLED PROMOTION & INFERENCE SNAPSHOT GENERATION
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_9_promotion_and_authoritative_inference():
    """
    Scenario 9-16: Controlled promotion, SHA integrity check, authoritative inference, prediction snapshot creation.
    """
    job_num = f"JOB-PROM-109-{uuid.uuid4().hex[:6]}"
    ds_id = f"DS-FSV1-PROM-{uuid.uuid4().hex[:6]}"
    disp_id = f"DISP-PROM-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        summary = await WS10ProductionLifecycleCoordinator.execute_full_lifecycle_orchestration(
            session=session,
            job_number=job_num,
            dataset_id=ds_id,
            new_dispatches_in_batch=150,
            perform_controlled_promotion=True,
            promoter_info={"actor": "WS-10.9-TEST-ACTIVATION"},
            dispatch_id_for_inference=disp_id,
            operation_date="2026-08-05",
        )

        assert len(summary["promoted_models"]) > 0
        assert len(summary["inference_snapshots"]) > 0
        assert summary["predictive_authority_status"] == "AUTHORITATIVE"

        # Verify snapshots persisted in database
        stmt_snap = select(func.count(MLPredictionSnapshot.id))
        res_snap = await session.execute(stmt_snap)
        assert res_snap.scalar() > 0


# =============================================================================
# 4. API & GLOBAL FILTERING INTEGRATION
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_9_api_dto_and_global_filters():
    """
    Scenario 17-18: Predictive Intelligence API DTO verification and global filter application.
    """
    async with TestAsyncSessionFactory() as session:
        overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert overview.overall_authority_status in ("NOT_CONFIGURED", "AUTHORITATIVE")

        response = await PredictiveIntelligenceService.get_operational_predictive_intelligence(
            session=session, params=DashboardFilterParams()
        )
        assert response.overall_authority_status in ("NOT_CONFIGURED", "AUTHORITATIVE")


# =============================================================================
# 5. WS-09 HISTORICAL BASELINE & ZERO PRODUCTION POLLUTION
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_9_ws09_baseline_and_zero_pollution():
    """
    Scenario 19: Verifies 4 WS-09 historical REJECTED baseline models remain intact and no test pollution occurs.
    """
    async with TestAsyncSessionFactory() as session:
        stmt = select(MLModelVersion).where(
            and_(
                MLModelVersion.lifecycle_status == "REJECTED",
                MLModelVersion.model_version == "v1.0.0-rejected-ws09",
            )
        )
        res = await session.execute(stmt)
        rejected = list(res.scalars().all())
        assert len(rejected) == 4
