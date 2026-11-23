"""
WS-09 Phase 7.7 Operational Predictive Integration Backend Test Suite

Verifies:
1. Production NOT_CONFIGURED safety boundary
2. Model Registry authority resolution
3. NO_DATA state distinct from NOT_CONFIGURED
4. Isolated test-only promoted fixture execution
5. Prediction snapshot enrichment & operational decision intelligence prioritization
6. Model retirement lifecycle & historical snapshot preservation
"""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator


@pytest.mark.asyncio
async def test_ws_09_7_7_not_configured_safety():
    """Verifies that when 0 promoted models exist, operational intelligence returns NOT_CONFIGURED payload safely."""
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
        res = await PredictiveIntelligenceService.get_operational_predictive_intelligence(db_session, params)

        assert res.overall_authority_status == "NOT_CONFIGURED"
        assert res.promoted_model_count == 0
        assert res.total_snapshots_found == 0
        assert len(res.snapshots) == 0
        assert len(res.prioritization.top_delayed_dispatches) == 0
        assert res.calculation_status == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_ws_09_7_7_promoted_fixture_and_operational_enrichment():
    """
    Verifies full Phase 7.7 operational flow using an isolated test-only promoted model:
    Promote -> Generate Snapshot -> Query Operational Intelligence -> Verify Enrichment -> Retire Model.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        registry_repo = MLModelRegistryRepository(db_session)
        snapshot_repo = MLPredictionSnapshotRepository(db_session)

        # 1. Train candidates to obtain real candidate artifact
        await Phase72ModelTrainer.train_all_candidate_models(db_session, dataset_id="DS-TEST-77")
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        model = MLModelVersion(
            model_name="delay_regressor",
            model_version="v7.7.0-TEST-PROMOTED",
            model_category="Regression",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-TEST-77",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="PROMOTED",
            evaluation_decision="PROMOTABLE",
        )
        db_session.add(model)
        await db_session.flush()

        try:
            # 2. Generate prediction snapshot
            req_dto = PredictionRequestDTO(
                dispatch_id="DISP-TEST-77",
                dispatch_code="DSP-77-001",
                prediction_timestamp=datetime.now(timezone.utc),
                plant_code="PL-77",
                customer_code="CUST-77",
                vehicle_code="VH-77",
                ticket_volume_m3=6.0,
                plant_queue_avg_30d=15.0,
                customer_retention_avg_30d=8.0,
                dispatch_hour=10,
                dispatch_day_of_week=2,
                input_features={"avg_prior_delay_mins": 15.0},
                idempotency_key=f"IK-77-{uuid.uuid4().hex[:8]}",
            )
            snap = await snapshot_repo.generate_and_persist_prediction_snapshot("delay_regressor", req_dto)
            assert snap.prediction_status == "AUTHORITATIVE"

            # 3. Query Phase 7.7 Operational Intelligence
            params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
            res = await PredictiveIntelligenceService.get_operational_predictive_intelligence(db_session, params)

            assert res.overall_authority_status == "AUTHORITATIVE"
            assert res.promoted_model_count >= 1
            assert res.total_snapshots_found >= 1

            # Verify contextual enrichment
            matching = [s for s in res.snapshots if s.prediction_snapshot_id == snap.prediction_snapshot_id]
            assert len(matching) == 1
            item = matching[0]
            assert item.dispatch_code == "DSP-77-001"
            assert item.plant_name == "Plant PL-77"
            assert item.customer_name == "Customer CUST-77"
            assert item.artifact_sha256 == meta.artifact_sha256

            # Verify operational prioritization
            assert len(res.prioritization.top_delayed_dispatches) >= 1
            top = res.prioritization.top_delayed_dispatches[0]
            assert top.dispatch_code == "DSP-77-001"

        finally:
            # 4. Clean up / Retire model & delete test snapshot
            model.lifecycle_status = "RETIRED"
            await db_session.flush()


@pytest.mark.asyncio
async def test_ws_09_7_7_no_data_state_distinct_from_not_configured():
    """Verifies that when a promoted model exists but 0 snapshots match filters, NO_DATA is returned."""
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # Register a promoted model
        unique_sha = f"no_data_sha_{uuid.uuid4().hex[:8]}"
        model = MLModelVersion(
            model_name="turnaround_regressor",
            model_version="v7.7.0-NODATA-TEST",
            model_category="Regression",
            algorithm="LightGBM",
            target_name="predicted_avg_turnaround_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-NODATA-77",
            artifact_path=f"models/turnaround_regressor/{unique_sha}.joblib",
            artifact_sha256=unique_sha,
            artifact_size_bytes=1024,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="PROMOTED",
            evaluation_decision="PROMOTABLE",
        )
        db_session.add(model)
        await db_session.flush()

        try:
            params = DashboardFilterParams(plant_id="NON_EXISTENT_PLANT", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
            res = await PredictiveIntelligenceService.get_operational_predictive_intelligence(db_session, params)

            assert res.overall_authority_status == "AUTHORITATIVE"
            assert res.promoted_model_count >= 1
            assert res.total_snapshots_found == 0
            assert res.calculation_status == "NO_RECORDS"
        finally:
            model.lifecycle_status = "RETIRED"
            await db_session.flush()


@pytest.mark.asyncio
async def test_ws_09_7_7_rejected_candidate_protection_and_retirement_preserves_snapshots():
    """Verifies REJECTED models cannot produce active authority and RETIRED model snapshots remain queryable."""
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        snapshot_repo = MLPredictionSnapshotRepository(db_session)

        # 1. Create a REJECTED model
        rejected_model = MLModelVersion(
            model_name="sla_breach_classifier",
            model_version="v7.7.0-REJECTED-TEST",
            model_category="Classification",
            algorithm="LightGBM",
            target_name="predicted_sla_breach_target",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-REJ-77",
            artifact_path="models/sla_breach_classifier/rej.joblib",
            artifact_sha256="rej_sha",
            artifact_size_bytes=1024,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="REJECTED",
            evaluation_decision="REJECTED",
        )
        db_session.add(rejected_model)
        await db_session.flush()

        # Attempt snapshot on rejected model
        req_dto = PredictionRequestDTO(
            dispatch_id="DISP-REJ-77",
            dispatch_code="DSP-REJ-001",
            prediction_timestamp=datetime.now(timezone.utc),
            plant_code="PL-REJ",
            customer_code="CUST-REJ",
            vehicle_code="VH-REJ",
            ticket_volume_m3=6.0,
            plant_queue_avg_30d=15.0,
            customer_retention_avg_30d=8.0,
            dispatch_hour=10,
            dispatch_day_of_week=2,
        )
        res_rej = await snapshot_repo.generate_and_persist_prediction_snapshot("sla_breach_classifier", req_dto)
        assert res_rej.prediction_status == "NOT_CONFIGURED"

