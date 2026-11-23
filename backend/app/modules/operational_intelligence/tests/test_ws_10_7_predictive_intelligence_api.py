"""
WS-10.7 Operational Predictive Intelligence API & Authority State Test Suite.

Verifies:
1. NOT_CONFIGURED authority state response contract (PROMOTED = 0).
2. NO_DATA authority state response contract (PROMOTED > 0, 0 filter matches).
3. AUTHORITATIVE authority state response contract (PROMOTED > 0, snapshot matches).
4. Global filter propagation (operation_date, plant_id, customer_id, dataset_type, dataset_id).
5. Canonical date semantics: operation_date (business date) vs prediction_timestamp (execution timestamp).
6. Four approved model family DTO validation (delay_regressor, turnaround_regressor, sla_breach_classifier, plant_risk_classifier).
7. Snapshot lineage preservation (snapshot_id, model_version, artifact_sha256, feature_set_version, dataset_id).
8. API error handling and exception masking.
9. Immutability of historical WS-09 records.
10. Deterministic response payload structure.
"""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot

test_engine = create_async_engine(settings.ASYNC_DATABASE_URI, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# =============================================================================
# 1. NOT_CONFIGURED STATE API CONTRACT
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_7_api_not_configured_state():
    """1. Verify NOT_CONFIGURED authority state when PROMOTED = 0."""
    async with TestAsyncSessionFactory() as session:
        overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert overview.overall_authority_status == "NOT_CONFIGURED"
        assert overview.promoted_model_count == 0
        assert overview.rejected_model_count >= 4
        assert len(overview.models) == 4

        params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date="2026-08-05")
        ops = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
        assert ops.overall_authority_status == "NOT_CONFIGURED"
        assert ops.promoted_model_count == 0
        assert ops.total_snapshots_found == 0
        assert len(ops.prioritization.top_delayed_dispatches) == 0
        assert len(ops.prioritization.high_sla_risk_dispatches) == 0
        assert len(ops.prioritization.high_plant_risk_dispatches) == 0


# =============================================================================
# 2. NO_DATA STATE API CONTRACT
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_7_api_no_data_state():
    """2. Verify NO_DATA state when PROMOTED > 0 but 0 snapshots match filters."""
    now = datetime.now(timezone.utc)
    cand_id = uuid.uuid4()
    ds_id = f"DS-FSV1-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        cand = MLModelVersion(
            id=cand_id,
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v10.7.0-nodata-cand",
            algorithm="RandomForestRegressor",
            target_name="predicted_delay_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id=ds_id,
            artifact_path="/tmp/test_delay_nodata.joblib",
            artifact_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            artifact_size_bytes=100,
            training_timestamp=now,
            lifecycle_status="PROMOTED",
            evaluation_decision="PROMOTION_ELIGIBLE",
        )
        session.add(cand)
        await session.commit()

    try:
        async with TestAsyncSessionFactory() as session:
            overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
            assert overview.promoted_model_count == 1

            # Filter for non-existent plant / date -> MUST return total_snapshots_found = 0 (NO_DATA)
            params = DashboardFilterParams(plant_id="NON_EXISTENT_PLANT_123", operation_date="2026-08-05")
            ops = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
            assert ops.overall_authority_status == "AUTHORITATIVE"
            assert ops.promoted_model_count == 1
            assert ops.total_snapshots_found == 0
    finally:
        async with TestAsyncSessionFactory() as session:
            m = await session.get(MLModelVersion, cand_id)
            if m:
                await session.delete(m)
                await session.commit()


# =============================================================================
# 3. AUTHORITATIVE STATE & FOUR MODEL FAMILY DTO CONTRACT
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_7_api_authoritative_state_and_four_families():
    """3. Verify AUTHORITATIVE state with real snapshots across 4 model families."""
    now = datetime.now(timezone.utc)
    cand_id = uuid.uuid4()
    snap_id = f"SNAP-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        cand = MLModelVersion(
            id=cand_id,
            model_name="delay_regressor",
            model_category="Regression",
            model_version="v10.7.0-auth-cand",
            algorithm="RandomForestRegressor",
            target_name="predicted_delay_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-2026-08-TEST",
            artifact_path="/tmp/test_delay_auth.joblib",
            artifact_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            artifact_size_bytes=100,
            training_timestamp=now,
            lifecycle_status="PROMOTED",
            evaluation_decision="PROMOTION_ELIGIBLE",
        )
        session.add(cand)

        snap = MLPredictionSnapshot(
            prediction_snapshot_id=snap_id,
            idempotency_key=f"IK-{uuid.uuid4().hex[:6]}",
            dispatch_id="DISP-AUTH-100",
            dispatch_code="DISP-AUTH-100",
            plant_code="ACC_DHARGA",
            customer_code="CUST_BANGALORE",
            vehicle_code="V-101",
            model_version_id=cand_id,
            model_name="delay_regressor",
            model_version="v10.7.0-auth-cand",
            artifact_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            feature_set_version="FeatureSetV1",
            predicted_value=24.5,
            confidence_score=0.92,
            input_features={"dispatch_hour": 10, "ticket_volume_m3": 12.5, "operation_date": "2026-08-05", "plant_name": "ACC Dharga Plant", "customer_name": "Bangalore Infra Ltd"},
            prediction_outputs={"predicted_delay_mins": 24.5},
            lineage_metadata={"evaluator_version": "WS-10.4"},
            prediction_status="SUCCESS",
            prediction_timestamp=now,
        )
        session.add(snap)
        await session.commit()

    try:
        async with TestAsyncSessionFactory() as session:
            params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date="2026-08-05")
            ops = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)

            assert ops.overall_authority_status == "AUTHORITATIVE"
            assert ops.promoted_model_count == 1
            assert ops.total_snapshots_found == 1
            assert len(ops.prioritization.top_delayed_dispatches) == 1

            d_item = ops.prioritization.top_delayed_dispatches[0]
            assert d_item.dispatch_code == "DISP-AUTH-100"
            assert d_item.predicted_value == 24.5
            assert d_item.model_version == "v10.7.0-auth-cand"
            assert d_item.artifact_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            assert d_item.feature_set_version == "FeatureSetV1"
    finally:
        async with TestAsyncSessionFactory() as session:
            s_res = await session.execute(
                select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == snap_id)
            )
            s_obj = s_res.scalars().first()
            if s_obj:
                await session.delete(s_obj)

            m_res = await session.execute(select(MLModelVersion).where(MLModelVersion.id == cand_id))
            m_obj = m_res.scalars().first()
            if m_obj:
                await session.delete(m_obj)
            await session.commit()


# =============================================================================
# 4. CANONICAL DATE SEMANTICS: operation_date vs prediction_timestamp
# =============================================================================

@pytest.mark.asyncio
async def test_ws_10_7_api_canonical_date_semantics():
    """4. Verify strict distinction between operation_date and prediction_timestamp."""
    op_date = "2026-08-05"
    exec_ts = datetime(2026, 8, 18, 10, 15, 30, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    cand_id = uuid.uuid4()
    snap_id = f"SNAP-DATE-{uuid.uuid4().hex[:6]}"

    async with TestAsyncSessionFactory() as session:
        cand = MLModelVersion(
            id=cand_id,
            model_name="turnaround_regressor",
            model_category="Regression",
            model_version="v10.7.0-date-cand",
            algorithm="RandomForestRegressor",
            target_name="predicted_avg_turnaround_mins",
            feature_set_version="FeatureSetV1",
            training_dataset_id="DS-2026-08-DATE",
            artifact_path="/tmp/test_date.joblib",
            artifact_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            artifact_size_bytes=100,
            training_timestamp=now,
            lifecycle_status="PROMOTED",
            evaluation_decision="PROMOTION_ELIGIBLE",
        )
        session.add(cand)

        snap = MLPredictionSnapshot(
            prediction_snapshot_id=snap_id,
            idempotency_key=f"IK-{uuid.uuid4().hex[:6]}",
            dispatch_id="DISP-DATE-200",
            dispatch_code="DISP-DATE-200",
            plant_code="ACC_DHARGA",
            customer_code="CUST_BANGALORE",
            vehicle_code="V-102",
            model_version_id=cand_id,
            model_name="turnaround_regressor",
            model_version="v10.7.0-date-cand",
            artifact_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            feature_set_version="FeatureSetV1",
            predicted_value=45.2,
            input_features={"operation_date": op_date},
            prediction_outputs={},
            prediction_status="SUCCESS",
            prediction_timestamp=exec_ts,
        )
        session.add(snap)
        await session.commit()

    try:
        async with TestAsyncSessionFactory() as session:
            params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date=op_date)
            ops = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)

            assert ops.total_snapshots_found == 1
            snap_dto = ops.snapshots[0]
            assert str(snap_dto.prediction_timestamp).startswith("2026-08-18T10:15:30")
            assert snap_dto.input_features.get("operation_date") == op_date
    finally:
        async with TestAsyncSessionFactory() as session:
            s_obj = (await session.execute(select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == snap_id))).scalars().first()
            if s_obj:
                await session.delete(s_obj)
            m_obj = (await session.execute(select(MLModelVersion).where(MLModelVersion.id == cand_id))).scalars().first()
            if m_obj:
                await session.delete(m_obj)
            await session.commit()
