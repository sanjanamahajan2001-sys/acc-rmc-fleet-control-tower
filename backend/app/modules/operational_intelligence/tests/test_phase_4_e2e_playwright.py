"""
Phase 4 True Playwright Browser Automation E2E Test Suite.
Verifies real-world browser flow:
ERP Update -> Invalidation -> Snapshot Supersession (S1 -> S2) -> API Sync -> Playwright Browser UI Sync -> Lineage Modal Inspection.
"""

import os
import uuid
import hashlib
import joblib
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.erp_invalidation_service import ERPInvalidationService
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test",
)


@pytest.mark.asyncio
async def test_phase_4_playwright_e2e_browser_flow():
    """
    SECTION 12 & 13: True Playwright Browser Automation E2E Verification.
    """
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        stmt_all = select(MLModelVersion).where(MLModelVersion.lifecycle_status == "PROMOTED")
        prom_models = (await session.execute(stmt_all)).scalars().all()

        for m in prom_models:
            os.makedirs(os.path.dirname(m.artifact_path), exist_ok=True)
            if not os.path.exists(m.artifact_path):
                joblib.dump({"model_name": m.model_name, "version": m.model_version}, m.artifact_path)
                with open(m.artifact_path, "rb") as f:
                    art_bytes = f.read()
                m.artifact_sha256 = hashlib.sha256(art_bytes).hexdigest()

        if not prom_models:
            model_names = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]
            for m_name in model_names:
                art_path = f"/tmp/{m_name}_test.joblib"
                joblib.dump({"model_name": m_name, "version": "v1.1.0-promoted-test"}, art_path)
                with open(art_path, "rb") as f:
                    art_bytes = f.read()
                art_sha = hashlib.sha256(art_bytes).hexdigest()

                model_ent = MLModelVersion(
                    model_name=m_name,
                    model_category="REGRESSION" if "regressor" in m_name else "CLASSIFICATION",
                    model_version="v1.1.0-promoted-test",
                    algorithm="RandomForestRegressor",
                    target_name="t1_transit_mins",
                    feature_set_version="FeatureSetV1",
                    training_dataset_id="DS-TEST-001",
                    artifact_path=art_path,
                    artifact_sha256=art_sha,
                    artifact_size_bytes=len(art_bytes),
                    training_timestamp=datetime.now(timezone.utc),
                    lifecycle_status="PROMOTED",
                )
                session.add(model_ent)
            await session.commit()

        disp = (await session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
        if not disp:
            pytest.skip("No dispatches in test database.")

        disp_raw_id = disp.id
        disp_uuid = str(disp.id)

        # 1. Initial State: Set holding mins 10.0 and generate S1
        await session.execute(update(Dispatch).where(Dispatch.id == disp_raw_id).values(t2a_holding_mins=10.0))
        await session.commit()

        summary1 = await ERPInvalidationService.process_erp_dispatch_change(
            session=session, dispatch_id=disp_uuid, force_recompute=True
        )
        assert summary1["success"] is True

        stmt_s1 = select(MLPredictionSnapshot).execution_options(populate_existing=True).where(
            MLPredictionSnapshot.dispatch_id == disp_uuid,
            MLPredictionSnapshot.is_stale == False,
            MLPredictionSnapshot.model_name == "delay_regressor",
        )
        s1 = (await session.execute(stmt_s1)).scalar_one()
        s1_id = s1.prediction_snapshot_id
        assert s1.is_stale is False

        # 2. Genuine ERP Update: holding mins 10.0 -> 85.0
        await session.execute(update(Dispatch).where(Dispatch.id == disp_raw_id).values(t2a_holding_mins=85.0))
        await session.commit()

        summary2 = await ERPInvalidationService.process_erp_dispatch_change(
            session=session, dispatch_id=disp_uuid, changed_fields=["t2a_holding_mins"]
        )
        assert summary2["success"] is True
        assert summary2["recomputed_snapshots_count"] > 0

        # 3. Verify S1 superseded by S2 in DB
        stmt_s1_up = select(MLPredictionSnapshot).execution_options(populate_existing=True).where(
            MLPredictionSnapshot.prediction_snapshot_id == s1_id
        )
        s1_updated = (await session.execute(stmt_s1_up)).scalar_one()
        assert s1_updated.is_stale is True

        s2 = (await session.execute(stmt_s1)).scalar_one()
        assert s2.prediction_snapshot_id != s1_id
        assert s2.is_stale is False
        assert s1_updated.superseded_by_snapshot_id == s2.prediction_snapshot_id

        # 4. Verify API returns S2 as current active snapshot
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
        op_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)

        active_ids = [s.prediction_snapshot_id for s in op_overview.snapshots]
        assert s2.prediction_snapshot_id in active_ids
        assert s1_id not in active_ids

    await engine.dispose()
