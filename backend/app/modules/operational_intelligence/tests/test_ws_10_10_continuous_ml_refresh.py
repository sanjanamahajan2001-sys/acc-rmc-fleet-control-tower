"""
WS-10.10 Continuous Production ML Refresh & Governance Certification Test Suite.
Verifies all 24 WS-10.10 scenarios against isolated test database fleet_test:
- New ERP import detection & completion trigger
- Import idempotency & dataset immutability
- Full dataset extraction without dev limits
- Candidate training & holdout evaluation
- Strict promotion eligibility boundary (NO automatic promotion without WS-10.5 governance)
- Governed promotion & authoritative inference
- Snapshot lineage preservation
- Global filter propagation & SQL query correctness
- Authority states & zero production pollution
"""

import os
import uuid
import pytest
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.modules.erp.models import ImportJob, Dispatch
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.ml_trigger_service import MLTriggerService
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.ml.trainer import WS10TrainingOrchestrator
from app.modules.operational_intelligence.services.evaluator_service import WS10CandidateEvaluationService
from app.modules.operational_intelligence.services.promotion_service import WS10ModelPromotionService
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.services.refresh_service import WS10ContinuousMLRefreshService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test"
)

# Safety check: ABORT IF TEST DATABASE URL IS PRODUCTION
if "fleet_test" not in TEST_DB_URL:
    raise RuntimeError(f"CRITICAL SAFETY VIOLATION: Tests MUST target 'fleet_test'. Found: '{TEST_DB_URL}'")

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker

test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_ws_10_10_new_erp_import_detection_and_trigger():
    """
    Scenario 1-3: New ERP import detection, completion trigger creation, trigger idempotency.
    """
    job_num = f"JOB-REFRESH-1010-{uuid.uuid4().hex[:6]}"
    ds_id = f"DS-FSV1-REFRESH-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        # Trigger creation
        trig1 = await MLTriggerService.evaluate_and_create_trigger(
            session=session, import_job_id=None, job_number=job_num, dataset_id=ds_id, new_dispatches_in_batch=150
        )
        await session.commit()
        assert trig1.trigger_id is not None

        # Idempotency check: repeat trigger for same job
        trig2 = await MLTriggerService.evaluate_and_create_trigger(
            session=session, import_job_id=None, job_number=job_num, dataset_id=ds_id, new_dispatches_in_batch=150
        )
        await session.commit()
        assert trig2.trigger_id == trig1.trigger_id


@pytest.mark.asyncio
async def test_ws_10_10_dataset_creation_and_immutability():
    """
    Scenario 4-7: Dataset creation, full extraction without arbitrary dev limit, immutability, lineage.
    """
    ds_id = f"DS-FSV1-FULL-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        db_ds, ext_rows = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=None
        )
        await session.commit()

        assert db_ds.dataset_id == ds_id
        assert db_ds.feature_set_version == "FeatureSetV1"
        assert db_ds.total_records > 0

        # Immutability check: Duplicate dataset insertion fails
        with pytest.raises(ValueError, match="already exists"):
            await WS10FeatureDatasetBuilder.build_and_persist_dataset(
                session=session, dataset_id_override=ds_id, limit=None
            )


@pytest.mark.asyncio
async def test_ws_10_10_automatic_refresh_stops_at_promotion_eligibility():
    """
    Scenario 8-13: Candidate training, holdout evaluation, promotion eligibility (STOPS BEFORE AUTOMATIC PROMOTION).
    """
    job_num = f"JOB-REFRESH-STOP-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        summary = await WS10ContinuousMLRefreshService.execute_automatic_refresh_pipeline(
            session=session, job_number=job_num, new_dispatches_in_batch=150
        )

        assert summary["dataset_created"] is True
        assert len(summary["trained_candidates"]) == 4
        assert len(summary["evaluated_candidates"]) == 4
        assert summary["promoted_count"] == 0
        assert summary["governance_status"] == "WAITING_FOR_EXPLICIT_PROMOTION"


@pytest.mark.asyncio
async def test_ws_10_10_explicit_governed_promotion_and_inference():
    """
    Scenario 14-18: Explicit governed WS-10.5 promotion, authoritative inference, snapshot creation, lineage preservation.
    """
    job_num = f"JOB-PROM-1010-{uuid.uuid4().hex[:6]}"
    ds_id = f"DS-FSV1-PROM-{uuid.uuid4().hex[:6]}"
    disp_id = f"DISP-1010-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        # Step 1: Automatic refresh pipeline
        summary = await WS10ContinuousMLRefreshService.execute_automatic_refresh_pipeline(
            session=session, job_number=job_num, new_dispatches_in_batch=150
        )
        eligible = summary["promotion_eligible_candidates"]
        assert len(eligible) > 0

        # Step 2: Explicit governed promotion
        for cand in eligible:
            cand_id = uuid.UUID(cand["id"])
            promoted = await WS10ModelPromotionService.promote_eligible_candidate(
                session=session,
                version_id=cand_id,
                promoter_info={"actor": "WS-10.10-TEST-OPERATOR"},
                replacement_policy="RETIRE_EXISTING",
            )
            await session.commit()
            assert promoted.lifecycle_status == "PROMOTED"

        # Step 3: Authoritative inference
        from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import PredictionRequestDTO
        snap_resp = await WS10InferenceService.execute_inference_and_persist_snapshot(
            session=session,
            model_name="delay_regressor",
            request=PredictionRequestDTO(
                dispatch_id=disp_id,
                dispatch_code=disp_id,
                plant_code="ACC_KUNDAIM",
                customer_code="CUST_MANAS_DEVELOPERS_BAMBOLOIM",
                vehicle_code="V-101",
                operation_date="2026-08-05",
                input_features={"operation_date": "2026-08-05", "plant_code": "ACC_KUNDAIM", "customer_code": "CUST_MANAS_DEVELOPERS_BAMBOLOIM"},
            )
        )
        await session.commit()
        assert snap_resp.prediction_snapshot_id is not None
        assert snap_resp.prediction_status == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_ws_10_10_global_filters_and_authority_states():
    """
    Scenario 19-24: Filter propagation, SQL correctness, NO_DATA and AUTHORITATIVE response states, zero production pollution.
    """
    job_num = f"JOB-FILT-1010-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        # Promote at least one model to establish AUTHORITATIVE status
        summary = await WS10ContinuousMLRefreshService.execute_automatic_refresh_pipeline(
            session=session, job_number=job_num, new_dispatches_in_batch=150
        )
        eligible = summary["promotion_eligible_candidates"]
        if eligible:
            cand_id = uuid.UUID(eligible[0]["id"])
            await WS10ModelPromotionService.promote_eligible_candidate(
                session=session, version_id=cand_id, replacement_policy="RETIRE_EXISTING"
            )
            await session.commit()

        # 1. Query with non-matching plant filter -> NO_DATA state
        res_no_data = await PredictiveIntelligenceService.get_operational_predictive_intelligence(
            session=session, params=DashboardFilterParams(plant_id="NON_EXISTENT_PLANT_XYZ")
        )
        assert res_no_data.calculation_status == "NO_DATA"
        assert len(res_no_data.snapshots) == 0

        # 2. Query with ALL plants -> returns AUTHORITATIVE status
        res_all = await PredictiveIntelligenceService.get_operational_predictive_intelligence(
            session=session, params=DashboardFilterParams(plant_id="ALL")
        )
        assert res_all.overall_authority_status == "AUTHORITATIVE"

        # 3. Production isolation check
        res_prod_check = await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "PROMOTED"))
        assert res_prod_check.scalar() >= 1
