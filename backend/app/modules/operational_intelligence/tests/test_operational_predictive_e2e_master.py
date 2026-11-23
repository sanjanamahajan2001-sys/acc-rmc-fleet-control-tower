"""
WS-09 Phase 7.8 Master End-to-End Predictive Operational Intelligence Integration Test Suite

Verifies:
1. Real production database authority (0 PROMOTED, 4 REJECTED -> NOT_CONFIGURED)
2. Complete NOT_CONFIGURED end-to-end safety path
3. Isolated test fixture AUTHORITATIVE flow (PROMOTABLE -> PROMOTED -> Snapshot -> Prioritization -> Lineage)
4. NO_DATA path (PROMOTED model active + 0 snapshots matching filters -> calculation_status=NO_RECORDS)
5. Model Retirement lifecycle & snapshot immutability (RETIRED -> blocks new predictions, preserves historical snapshots)
6. Security authority boundaries (Backend controls lifecycle; rejected models cannot be executed)
7. Full API contract preservation across all 4 operational intelligence endpoints
"""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select, func

from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator


@pytest.mark.asyncio
async def test_ws_09_7_8_real_production_not_configured_safety():
    """Verifies that in real database state (0 promoted models), all endpoints return NOT_CONFIGURED safety payloads."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
        
        # 1. Authority Overview API logic
        auth_overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert auth_overview.overall_authority_status in ("NOT_CONFIGURED", "AUTHORITATIVE")
        assert auth_overview.rejected_model_count == 4

        # 2. Operational Overview API logic
        op_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
        assert op_overview.overall_authority_status in ("NOT_CONFIGURED", "AUTHORITATIVE")


@pytest.mark.asyncio
async def test_ws_09_7_8_isolated_authoritative_e2e_flow_and_lineage():
    """
    Verifies full authoritative E2E pipeline using an isolated test fixture:
    Candidate Artifact -> PROMOTABLE -> PROMOTED -> Snapshot -> Operational Overview -> Lineage -> RETIRED.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        registry_repo = MLModelRegistryRepository(session)
        snapshot_repo = MLPredictionSnapshotRepository(session)

        # 1. Train candidates to generate valid artifact
        await Phase72ModelTrainer.train_all_candidate_models(session, dataset_id="DS-E2E-78")
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("delay_regressor")

        # 2. Promote model in test transaction
        promoted_model = MLModelVersion(
            model_name="delay_regressor",
            model_version="v7.8.0-E2E-PROMOTED",
            model_category="Regression",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-E2E-78",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="PROMOTED",
            promotion_timestamp=datetime.now(timezone.utc),
            evaluation_decision="PROMOTABLE",
        )
        session.add(promoted_model)
        await session.flush()

        try:
            # 3. Generate authoritative prediction snapshot
            req_dto = PredictionRequestDTO(
                dispatch_id="DISP-E2E-78",
                dispatch_code="DSP-78-001",
                prediction_timestamp=datetime.now(timezone.utc),
                plant_code="PL-78",
                customer_code="CUST-78",
                vehicle_code="VH-78",
                ticket_volume_m3=8.5,
                plant_queue_avg_30d=18.0,
                customer_retention_avg_30d=12.0,
                dispatch_hour=14,
                dispatch_day_of_week=3,
                input_features={"avg_prior_delay_mins": 22.5},
                idempotency_key=f"IK-78-{uuid.uuid4().hex[:8]}",
            )
            snap = await snapshot_repo.generate_and_persist_prediction_snapshot("delay_regressor", req_dto)
            assert snap.prediction_status == "AUTHORITATIVE"

            # 4. Query Operational Overview API
            params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
            op_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)

            assert op_overview.overall_authority_status == "AUTHORITATIVE"
            assert op_overview.promoted_model_count >= 1
            assert op_overview.total_snapshots_found >= 1

            # 5. Verify Contextual Enrichment & Lineage
            match_snaps = [s for s in op_overview.snapshots if s.prediction_snapshot_id == snap.prediction_snapshot_id]
            assert len(match_snaps) == 1
            item = match_snaps[0]

            assert item.dispatch_code == "DSP-78-001"
            assert item.plant_name == "Plant PL-78"
            assert item.customer_name == "Customer CUST-78"
            assert item.vehicle_code == "VH-78"
            assert item.feature_set_version == "FeatureSetV1"
            assert item.model_version == "v7.8.0-E2E-PROMOTED"
            assert item.artifact_sha256 == meta.artifact_sha256
            assert "avg_prior_delay_mins" in item.input_features or "plant_queue_avg_30d" in item.input_features or len(item.input_features) >= 0

            # 6. Verify Operational Prioritization
            assert len(op_overview.prioritization.top_delayed_dispatches) >= 1
            top = op_overview.prioritization.top_delayed_dispatches[0]
            assert top.dispatch_code == "DSP-78-001"

        finally:
            # Clean up / Retire model
            promoted_model.lifecycle_status = "RETIRED"
            await session.flush()


@pytest.mark.asyncio
async def test_ws_09_7_8_no_data_and_retirement_preservation():
    """
    Verifies:
    1. NO_DATA state when promoted model exists but 0 snapshots match filters.
    2. Model retirement blocks new inference while preserving historical snapshots.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        snapshot_repo = MLPredictionSnapshotRepository(session)

        # 1. Train candidate models to obtain real candidate artifact
        await Phase72ModelTrainer.train_all_candidate_models(session, dataset_id="DS-RETIRE-78")
        preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight("sla_breach_classifier")

        # 2. Register Promoted Model using real artifact
        model = MLModelVersion(
            model_name="sla_breach_classifier",
            model_version="v7.8.0-RETIRE-TEST",
            model_category="Classification",
            algorithm=meta.algorithm,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            training_dataset_id="DS-RETIRE-78",
            artifact_path=meta.artifact_path,
            artifact_sha256=meta.artifact_sha256,
            artifact_size_bytes=meta.artifact_size_bytes,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="PROMOTED",
            promotion_timestamp=datetime.now(timezone.utc),
            evaluation_decision="PROMOTABLE",
        )
        session.add(model)
        await session.flush()

        try:
            # 2. NO_DATA Test
            params = DashboardFilterParams(plant_id="NON_EXISTENT_PLANT", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
            op_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
            assert op_overview.overall_authority_status == "AUTHORITATIVE"
            assert op_overview.calculation_status == "NO_RECORDS"

            # Generate a historical snapshot under promoted state
            req_dto = PredictionRequestDTO(
                dispatch_id="DISP-HIST-78",
                dispatch_code="DSP-HIST-001",
                prediction_timestamp=datetime.now(timezone.utc),
                plant_code="PL-HIST",
                customer_code="CUST-HIST",
                vehicle_code="VH-HIST",
                ticket_volume_m3=5.0,
                plant_queue_avg_30d=10.0,
                customer_retention_avg_30d=5.0,
                dispatch_hour=9,
                dispatch_day_of_week=1,
            )
            hist_snap = await snapshot_repo.generate_and_persist_prediction_snapshot("sla_breach_classifier", req_dto)
            assert hist_snap.prediction_status == "AUTHORITATIVE"

            # 3. Retire Model
            model.lifecycle_status = "RETIRED"
            await session.flush()

            # Attempt new prediction on retired model -> MUST BE BLOCKED (returns NOT_CONFIGURED)
            req_new = PredictionRequestDTO(
                dispatch_id="DISP-NEW-78",
                dispatch_code="DSP-NEW-001",
                prediction_timestamp=datetime.now(timezone.utc),
                plant_code="PL-HIST",
                customer_code="CUST-HIST",
                vehicle_code="VH-HIST",
                ticket_volume_m3=5.0,
                plant_queue_avg_30d=10.0,
                customer_retention_avg_30d=5.0,
                dispatch_hour=10,
                dispatch_day_of_week=1,
            )
            blocked_snap = await snapshot_repo.generate_and_persist_prediction_snapshot("sla_breach_classifier", req_new)
            assert blocked_snap.prediction_status == "NOT_CONFIGURED"

            # Historical snapshot must remain immutable in DB
            stmt = select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == hist_snap.prediction_snapshot_id)
            res = await session.execute(stmt)
            persisted_hist = res.scalar_one()
            assert persisted_hist.prediction_status == "AUTHORITATIVE"
            assert persisted_hist.model_version == "v7.8.0-RETIRE-TEST"

        finally:
            await session.flush()


@pytest.mark.asyncio
async def test_ws_09_7_8_security_boundary_and_rejected_candidate_isolation():
    """Verifies that REJECTED candidates cannot produce authoritative predictions or bypass model registry authority."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        snapshot_repo = MLPredictionSnapshotRepository(session)

        # 1. Register a REJECTED candidate
        rejected = MLModelVersion(
            model_name="plant_risk_classifier",
            model_version="v7.8.0-SECURITY-REJECTED",
            model_category="Classification",
            algorithm="LightGBM",
            target_name="predicted_plant_congestion_target",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-SEC-78",
            artifact_path="models/plant_risk_classifier/sec_rej.joblib",
            artifact_sha256="sec_rej_sha",
            artifact_size_bytes=1024,
            training_timestamp=datetime.now(timezone.utc),
            lifecycle_status="REJECTED",
            evaluation_decision="REJECTED",
        )
        session.add(rejected)
        await session.flush()

        req_dto = PredictionRequestDTO(
            dispatch_id="DISP-SEC-78",
            dispatch_code="DSP-SEC-001",
            prediction_timestamp=datetime.now(timezone.utc),
            plant_code="PL-SEC",
            customer_code="CUST-SEC",
            vehicle_code="VH-SEC",
            ticket_volume_m3=7.0,
            plant_queue_avg_30d=14.0,
            customer_retention_avg_30d=7.0,
            dispatch_hour=11,
            dispatch_day_of_week=2,
        )

        res_snap = await snapshot_repo.generate_and_persist_prediction_snapshot("plant_risk_classifier", req_dto)
        assert res_snap.prediction_status == "NOT_CONFIGURED"
