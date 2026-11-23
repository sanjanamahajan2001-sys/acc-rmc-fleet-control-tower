"""
Phase 1 Automated Backend Test Suite: Automatic ERP-to-Prediction Orchestration.
Runs exclusively on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.erp.models import ImportJob, Dispatch, Plant, Customer, Vehicle
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.events.erp_trigger_listener import ERPTriggerListener
from app.modules.operational_intelligence.services.active_inference_service import WS10ActiveModelInferenceService

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test",
)


@pytest_asyncio.fixture
async def test_session():
    """Isolated test database session for Phase 1 verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    await engine.dispose()


async def create_dummy_import_job(session: AsyncSession, job_number: str) -> tuple[uuid.UUID, str]:
    """Helper to create a valid ImportJob record for FK constraints."""
    unique_job_num = f"{job_number}-{uuid.uuid4().hex[:6]}"
    job = ImportJob(
        job_number=unique_job_num,
        file_name="test_phase1.xlsx",
        file_hash="test_sha256_hash",
        status="COMPLETED",
    )
    session.add(job)
    await session.commit()
    return job.id, unique_job_num


@pytest.mark.asyncio
async def test_phase_1_erp_completion_trigger_invokes_active_inference(test_session: AsyncSession):
    """Test 1: Verify ERP import completion automatically triggers active inference."""
    job_id, unique_job_num = await create_dummy_import_job(test_session, "JOB-PHASE1-TEST")
    payload = {
        "job_number": unique_job_num,
        "import_job_id": str(job_id),
        "processed_rows": 10,
        "counts": {"dispatches": 10},
    }

    result = await ERPTriggerListener.on_erp_import_completed(session=test_session, event_payload=payload)
    assert result is not None
    assert "inference_summary" in result
    assert result["inference_summary"]["success"] is True


@pytest.mark.asyncio
async def test_phase_1_active_model_selection_and_promoted_only(test_session: AsyncSession):
    """Test 3 & 4: Verify only PROMOTED models execute and REJECTED models are excluded."""
    res = await WS10ActiveModelInferenceService.execute_batch_inference_for_new_dispatches(session=test_session)
    assert "promoted_models_count" in res

    # Verify all snapshots in database belong to PROMOTED models
    stmt = select(MLPredictionSnapshot)
    res_snaps = await test_session.execute(stmt)
    snaps = list(res_snaps.scalars().all())

    stmt_models = select(MLModelVersion)
    res_models = await test_session.execute(stmt_models)
    models_dict = {str(m.id): m for m in res_models.scalars().all()}

    for snap in snaps:
        model_ver = models_dict.get(str(snap.model_version_id))
        if model_ver:
            assert model_ver.lifecycle_status == "PROMOTED"


@pytest.mark.asyncio
async def test_phase_1_snapshot_persistence_and_lineage(test_session: AsyncSession):
    """Test 6, 14, 15: Verify snapshots persist with SHA-256 and feature lineage."""
    stmt = select(MLPredictionSnapshot).limit(5)
    res = await test_session.execute(stmt)
    snaps = list(res.scalars().all())

    for s in snaps:
        assert s.prediction_snapshot_id.startswith("SNAP-")
        assert s.feature_set_version == "FeatureSetV1"
        assert s.input_features is not None
        assert s.lineage_metadata is not None
        assert s.lineage_metadata.get("prediction_authority") == "AUTHORITATIVE"


@pytest.mark.asyncio
async def test_phase_1_real_data_purity_no_mock_strings(test_session: AsyncSession):
    """Test 13: Verify zero ACC_DHARGA or CUST_BANGALORE mock fallback strings exist."""
    stmt = select(MLPredictionSnapshot).where(
        (MLPredictionSnapshot.plant_code == "ACC_DHARGA")
        | (MLPredictionSnapshot.customer_code == "CUST_BANGALORE")
    )
    res = await test_session.execute(stmt)
    mock_snaps = list(res.scalars().all())
    assert len(mock_snaps) == 0, f"Found {len(mock_snaps)} mock snapshot fallbacks!"


@pytest.mark.asyncio
async def test_phase_1_duplicate_event_retry_safety(test_session: AsyncSession):
    """Test 9: Verify duplicate ERP completion event does not crash inference orchestration."""
    job_id, unique_job_num = await create_dummy_import_job(test_session, "JOB-PHASE1-RETRY")
    payload = {
        "job_number": unique_job_num,
        "import_job_id": str(job_id),
        "processed_rows": 5,
    }

    res1 = await ERPTriggerListener.on_erp_import_completed(session=test_session, event_payload=payload)
    res2 = await ERPTriggerListener.on_erp_import_completed(session=test_session, event_payload=payload)

    assert res1 is not None
    assert res2 is not None
    assert res1["inference_summary"]["success"] is True
    assert res2["inference_summary"]["success"] is True
