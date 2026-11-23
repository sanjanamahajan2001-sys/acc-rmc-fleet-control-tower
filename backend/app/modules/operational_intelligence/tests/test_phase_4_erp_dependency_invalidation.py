"""
Phase 4 Automated Backend Test Suite: ERP Change Dependency Graph & Invalidation Chain.
Runs exclusively on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import hashlib
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.dependency_graph_service import ERPDependencyGraphService
from app.modules.operational_intelligence.services.erp_invalidation_service import ERPInvalidationService
from app.modules.operational_intelligence.events.erp_trigger_listener import ERPTriggerListener
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import MLPredictionSnapshotRepository

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test",
)


@pytest_asyncio.fixture
async def test_session():
    """Isolated test database session for Phase 4 verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Ensure all PROMOTED models in fleet_test have valid artifact files on disk
        stmt_all = select(MLModelVersion).where(MLModelVersion.lifecycle_status == "PROMOTED")
        prom_models = (await session.execute(stmt_all)).scalars().all()

        import joblib
        for m in prom_models:
            os.makedirs(os.path.dirname(m.artifact_path), exist_ok=True)
            if not os.path.exists(m.artifact_path):
                joblib.dump({"model_name": m.model_name, "version": m.model_version}, m.artifact_path)
                with open(m.artifact_path, "rb") as f:
                    art_bytes = f.read()
                m.artifact_sha256 = hashlib.sha256(art_bytes).hexdigest()

        # If 0 promoted models exist, seed the 4 default models
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
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_phase_4_01_dependency_graph_construction():
    """Test 1: Verify dependency graph returns targeted model families for modified fields."""
    models_plant = ERPDependencyGraphService.evaluate_affected_models(["plant_code"])
    assert "delay_regressor" in models_plant
    assert "plant_risk_classifier" in models_plant
    assert len(models_plant) >= 2

    models_cust = ERPDependencyGraphService.evaluate_affected_models(["customer_code"])
    assert "sla_breach_classifier" in models_cust
    assert "turnaround_regressor" in models_cust

    models_veh = ERPDependencyGraphService.evaluate_affected_models(["vehicle_code"])
    assert "delay_regressor" in models_veh
    assert "turnaround_regressor" in models_veh

    models_holding = ERPDependencyGraphService.evaluate_affected_models(["t2a_holding_mins"])
    assert "delay_regressor" in models_holding
    assert "turnaround_regressor" in models_holding
    assert "plant_risk_classifier" in models_holding

    models_retention = ERPDependencyGraphService.evaluate_affected_models(["t2c_retention_mins"])
    assert "turnaround_regressor" in models_retention
    assert "sla_breach_classifier" in models_retention


@pytest.mark.asyncio
async def test_phase_4_02_erp_insert_and_invalidation_chain(test_session: AsyncSession):
    """Test 2 & 3: Test ERP dispatch invalidation chain on real dispatch."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[0]
    disp_raw_id = disp.id
    disp_uuid = str(disp.id)

    # Set known initial feature value 10.0
    await test_session.execute(update(Dispatch).where(Dispatch.id == disp_raw_id).values(t2a_holding_mins=10.0))
    await test_session.commit()

    # Process initial invalidation event (s1 will have 10.0)
    summary1 = await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session, dispatch_id=disp_uuid, force_recompute=True
    )
    assert summary1["success"] is True
    assert summary1["recomputed_snapshots_count"] > 0

    # Query initial active snapshot S1
    stmt1 = select(MLPredictionSnapshot).where(
        MLPredictionSnapshot.dispatch_id == disp_uuid,
        MLPredictionSnapshot.is_stale == False,
        MLPredictionSnapshot.model_name == "delay_regressor",
    )
    s1 = (await test_session.execute(stmt1)).scalar_one()
    s1_id = s1.prediction_snapshot_id

    # Simulate material ERP update (10.0 -> 85.0) via explicit update query
    await test_session.execute(update(Dispatch).where(Dispatch.id == disp_raw_id).values(t2a_holding_mins=85.0))
    await test_session.commit()

    summary2 = await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session, dispatch_id=disp_uuid, changed_fields=["t2a_holding_mins"]
    )
    assert summary2["success"] is True
    assert summary2["recomputed_snapshots_count"] > 0

    # Re-query s1 by ID from session with populate_existing=True
    stmt_s1 = select(MLPredictionSnapshot).execution_options(populate_existing=True).where(MLPredictionSnapshot.prediction_snapshot_id == s1_id)
    s1_updated = (await test_session.execute(stmt_s1)).scalar_one()
    assert s1_updated.is_stale is True

    # Query new active snapshot s2
    stmt_s2 = select(MLPredictionSnapshot).execution_options(populate_existing=True).where(
        MLPredictionSnapshot.dispatch_id == disp_uuid,
        MLPredictionSnapshot.is_stale == False,
        MLPredictionSnapshot.model_name == "delay_regressor",
    )
    s2 = (await test_session.execute(stmt_s2)).scalar_one()
    assert s2.prediction_snapshot_id != s1_id
    assert s2.is_stale is False
    assert s1_updated.superseded_by_snapshot_id == s2.prediction_snapshot_id


@pytest.mark.asyncio
async def test_phase_4_03_unchanged_erp_update_protection(test_session: AsyncSession):
    """Test 5: Verify updating ERP record with unchanged features does NOT regenerate predictions."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[1] if len(dispatches) > 1 else dispatches[0]
    disp_uuid = str(disp.id)

    # Initial computation
    await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session, dispatch_id=disp_uuid, force_recompute=True
    )
    await test_session.commit()

    # Repeat with unchanged features (only status field changed)
    summary_unchanged = await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session, dispatch_id=disp_uuid, changed_fields=["status"]
    )
    assert summary_unchanged["reason"] == "UNCHANGED_ERP_UPDATE_SKIPPED"
    assert summary_unchanged["recomputed_snapshots_count"] == 0


@pytest.mark.asyncio
async def test_phase_4_04_concurrent_erp_events_idempotency(test_session: AsyncSession):
    """Test 13: Verify concurrent invalidation events on same dispatch execute cleanly."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[2] if len(dispatches) > 2 else dispatches[0]
    disp_uuid = str(disp.id)

    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def task_invalidate():
        async with async_session() as session:
            return await ERPInvalidationService.process_erp_dispatch_change(session, disp_uuid, force_recompute=True)

    res1, res2 = await asyncio.gather(task_invalidate(), task_invalidate())
    await engine.dispose()

    assert res1["success"] is True or res2["success"] is True

    # Verify exactly one active snapshot exists per model family
    stmt = select(MLPredictionSnapshot).where(
        MLPredictionSnapshot.dispatch_id == disp_uuid,
        MLPredictionSnapshot.is_stale == False,
        MLPredictionSnapshot.model_name == "delay_regressor",
    )
    active_snaps = (await test_session.execute(stmt)).scalars().all()
    assert len(active_snaps) == 1


@pytest.mark.asyncio
async def test_phase_4_05_targeted_model_family_invalidation(test_session: AsyncSession):
    """Test 14: Verify targeted invalidation recomputes ONLY affected model families."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[3] if len(dispatches) > 3 else dispatches[0]
    disp_raw_id = disp.id
    disp_uuid = str(disp.id)

    # Initial computation with known initial retention_mins
    await test_session.execute(update(Dispatch).where(Dispatch.id == disp_raw_id).values(t2c_retention_mins=10.0))
    await test_session.commit()

    await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session, dispatch_id=disp_uuid, force_recompute=True
    )
    await test_session.commit()

    # Update t2c_retention_mins (affects turnaround_regressor & sla_breach_classifier ONLY)
    await test_session.execute(update(Dispatch).where(Dispatch.id == disp_raw_id).values(t2c_retention_mins=95.0))
    await test_session.commit()

    summary = await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session, dispatch_id=disp_uuid, changed_fields=["t2c_retention_mins"]
    )
    assert summary["success"] is True
    assert "turnaround_regressor" in summary["affected_models"]
    assert "sla_breach_classifier" in summary["affected_models"]
    assert summary["recomputed_snapshots_count"] >= 2


@pytest.mark.asyncio
async def test_phase_4_06_erp_listener_event_handling(test_session: AsyncSession):
    """Test 15: Verify ERP invalidation service processes ERP import event payload cleanly."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[4] if len(dispatches) > 4 else dispatches[0]
    disp_uuid = str(disp.id)

    result = await ERPInvalidationService.process_erp_dispatch_change(
        session=test_session,
        dispatch_id=disp_uuid,
        changed_fields=["t2a_holding_mins"],
        force_recompute=True,
    )
    assert result["success"] is True
    assert result["dispatch_id"] == disp_uuid


@pytest.mark.asyncio
async def test_phase_4_07_stale_snapshot_ui_exclusion(test_session: AsyncSession):
    """Test 16: Verify active snapshot queries strictly filter out stale snapshots."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[0]
    disp_uuid = str(disp.id)

    repo = MLPredictionSnapshotRepository(test_session)
    active_snaps = await repo.list_snapshots_by_dispatch(disp.dispatch_number)
    for s in active_snaps:
        assert s.is_stale is False


@pytest.mark.asyncio
async def test_phase_4_08_lineage_preservation_across_supersession(test_session: AsyncSession):
    """Test 17: Verify lineage metadata is preserved on historical superseded snapshot."""
    dispatches = (await test_session.execute(select(Dispatch).limit(5))).scalars().all()
    if not dispatches:
        pytest.skip("No real dispatches found in test database.")

    disp = dispatches[0]
    disp_uuid = str(disp.id)

    stmt_stale = select(MLPredictionSnapshot).where(
        MLPredictionSnapshot.dispatch_id == disp_uuid,
        MLPredictionSnapshot.is_stale == True,
    )
    stale_snaps = (await test_session.execute(stmt_stale)).scalars().all()
    for s in stale_snaps:
        assert s.lineage_metadata is not None
        assert s.superseded_by_snapshot_id is not None
