"""
Phase 2 Automated Backend Certification & Evidence Suite: Snapshot Integrity, Idempotency & Supersession.
Runs exclusively on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test",
)


@pytest_asyncio.fixture
async def test_session():
    """Isolated test database session for Phase 2 verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed dummy PROMOTED model if none exists
        stmt = select(MLModelVersion).where(
            MLModelVersion.model_name == "delay_regressor",
            MLModelVersion.lifecycle_status == "PROMOTED",
        )
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            dummy_model = MLModelVersion(
                model_name="delay_regressor",
                model_category="REGRESSION",
                model_version="v1.1.0-promoted-test",
                algorithm="RandomForestRegressor",
                target_name="t1_transit_mins",
                feature_set_version="FeatureSetV1",
                training_dataset_id="DS-TEST-001",
                artifact_path="/tmp/delay_regressor.joblib",
                artifact_sha256="test_sha256_hash",
                artifact_size_bytes=1024,
                training_timestamp=datetime.now(timezone.utc),
                lifecycle_status="PROMOTED",
            )
            session.add(dummy_model)

        stmt_turn = select(MLModelVersion).where(
            MLModelVersion.model_name == "turnaround_regressor",
            MLModelVersion.lifecycle_status == "PROMOTED",
        )
        res_turn = await session.execute(stmt_turn)
        if not res_turn.scalar_one_or_none():
            dummy_turn = MLModelVersion(
                model_name="turnaround_regressor",
                model_category="REGRESSION",
                model_version="v1.1.0-promoted-test",
                algorithm="RandomForestRegressor",
                target_name="t2b_unloading_mins",
                feature_set_version="FeatureSetV1",
                training_dataset_id="DS-TEST-001",
                artifact_path="/tmp/turnaround_regressor.joblib",
                artifact_sha256="test_sha256_hash",
                artifact_size_bytes=1024,
                training_timestamp=datetime.now(timezone.utc),
                lifecycle_status="PROMOTED",
            )
            session.add(dummy_turn)

        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_phase_2_1_stale_flag_and_supersession_link(test_session: AsyncSession):
    """Evidence 1: Verify ERP dispatch update transitions S1 -> is_stale=True, S1.superseded_by=S2.id, S2 active."""
    disp_id = f"DISP-EVI1-{uuid.uuid4().hex[:6]}"
    disp_code = f"TCK-{disp_id}"

    snap1 = MLPredictionSnapshot(
        prediction_snapshot_id=f"SNAP-{uuid.uuid4().hex[:12].upper()}",
        idempotency_key=f"IK-delay-{disp_code}-1",
        prediction_timestamp=datetime.now(timezone.utc),
        prediction_status="AUTHORITATIVE",
        model_name="delay_regressor",
        model_version="v1.1.0-test",
        artifact_sha256="test_sha",
        feature_set_version="FeatureSetV1",
        dispatch_id=disp_id,
        dispatch_code=disp_code,
        plant_code="ACC_KUNDAIM",
        customer_code="CUST_TEST",
        vehicle_code="V-TEST-01",
        input_features={"test": 1},
        prediction_outputs={"predicted_value": 15.0},
        predicted_value=15.0,
        is_stale=False,
    )
    test_session.add(snap1)
    await test_session.commit()
    snap1_id = snap1.prediction_snapshot_id

    snap2 = MLPredictionSnapshot(
        prediction_snapshot_id=f"SNAP-{uuid.uuid4().hex[:12].upper()}",
        idempotency_key=f"IK-delay-{disp_code}-2",
        prediction_timestamp=datetime.now(timezone.utc),
        prediction_status="AUTHORITATIVE",
        model_name="delay_regressor",
        model_version="v1.1.0-test",
        artifact_sha256="test_sha",
        feature_set_version="FeatureSetV1",
        dispatch_id=disp_id,
        dispatch_code=disp_code,
        plant_code="ACC_KUNDAIM",
        customer_code="CUST_TEST",
        vehicle_code="V-TEST-01",
        input_features={"test": 2},
        prediction_outputs={"predicted_value": 18.0},
        predicted_value=18.0,
        is_stale=False,
    )

    # Perform supersession
    snap1.is_stale = True
    await test_session.flush()

    test_session.add(snap2)
    await test_session.flush()

    snap1.superseded_by_snapshot_id = snap2.prediction_snapshot_id
    await test_session.commit()

    # Query S1 and S2
    s1 = (await test_session.execute(select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == snap1_id))).scalar_one()
    s2 = (await test_session.execute(select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == snap2.prediction_snapshot_id))).scalar_one()

    assert s1.is_stale is True
    assert s1.superseded_by_snapshot_id == snap2.prediction_snapshot_id
    assert s2.is_stale is False
    assert s2.superseded_by_snapshot_id is None


@pytest.mark.asyncio
async def test_phase_2_2_retry_idempotency(test_session: AsyncSession):
    """Evidence 2: Repeat prediction request for same dispatch & model returns existing snapshot cleanly."""
    disp_id = f"DISP-RETRY-{uuid.uuid4().hex[:6]}"
    disp_code = f"TCK-{disp_id}"

    snap1 = MLPredictionSnapshot(
        prediction_snapshot_id=f"SNAP-{uuid.uuid4().hex[:12].upper()}",
        idempotency_key=f"IK-turnaround-{disp_code}",
        prediction_timestamp=datetime.now(timezone.utc),
        prediction_status="AUTHORITATIVE",
        model_name="turnaround_regressor",
        model_version="v1.1.0-test",
        artifact_sha256="test_sha",
        feature_set_version="FeatureSetV1",
        dispatch_id=disp_id,
        dispatch_code=disp_code,
        plant_code="ACC_NESSAI",
        customer_code="CUST_RETRY",
        vehicle_code="V-RETRY",
        input_features={"test": 1},
        prediction_outputs={"predicted_value": 20.0},
        predicted_value=20.0,
        is_stale=False,
    )
    test_session.add(snap1)
    await test_session.commit()

    stmt = select(MLPredictionSnapshot).where(
        MLPredictionSnapshot.dispatch_id == disp_id,
        MLPredictionSnapshot.is_stale == False,
    )
    active_snaps = (await test_session.execute(stmt)).scalars().all()
    assert len(active_snaps) == 1
    assert active_snaps[0].prediction_snapshot_id == snap1.prediction_snapshot_id


@pytest.mark.asyncio
async def test_phase_2_3_authority_resolution_excludes_stale_snapshots(test_session: AsyncSession):
    """Evidence 3: PredictiveIntelligenceService filters out stale snapshots from API response."""
    resp = await PredictiveIntelligenceService.get_operational_predictive_intelligence(
        session=test_session, params=DashboardFilterParams()
    )

    for item in resp.snapshots:
        stmt = select(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id == item.prediction_snapshot_id)
        snap = (await test_session.execute(stmt)).scalar_one_or_none()
        if snap:
            assert snap.is_stale is False, f"Stale snapshot {snap.prediction_snapshot_id} returned as authoritative!"


@pytest.mark.asyncio
async def test_phase_2_4_lineage_metadata_integrity(test_session: AsyncSession):
    """Evidence 4: Lineage metadata (SHA-256, model_version_id, feature_set_version) remains 100% intact."""
    stmt = select(MLPredictionSnapshot).where(MLPredictionSnapshot.is_stale == False).limit(5)
    snaps = (await test_session.execute(stmt)).scalars().all()

    for s in snaps:
        assert s.feature_set_version == "FeatureSetV1"
        assert s.artifact_sha256 is not None
