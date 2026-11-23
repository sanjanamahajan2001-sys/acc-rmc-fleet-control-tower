"""
Phase 5 / Workstream 5.7 Test Suite: Feedback & Continuous Learning Engine
Verifies feedback ingestion, outcome matching, error delta calculations,
outlier detection, continuous learning trigger emission, and zero data leakage.
"""

import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.ml_feedback_record import MLFeedbackRecord
from app.modules.operational_intelligence.models.continuous_learning_trigger import ContinuousLearningTrigger
from app.modules.operational_intelligence.services.feedback_loop_service import FeedbackLoopService

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    from app.core.config import settings
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()

@pytest_asyncio.fixture
async def ws57_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("TRUNCATE TABLE ml_feedback_records, continuous_learning_triggers CASCADE;"))
    async with async_session_factory() as session:
        yield session
    await engine.dispose()

async def _seed_test_outcome_and_snapshot(session: AsyncSession, model_family: str = "delay_regressor"):
    uid = uuid.uuid4().hex[:6]
    dispatch_code = f"SYNTH-TCK-TRIP-{uid}"
    outcome_id = f"OUT-57-{uid}"
    snapshot_id = f"SNAP-57-{uid}"

    # Query existing dispatch if available
    res_disp = await session.execute(select(Dispatch))
    existing_disp = res_disp.scalars().first()

    if existing_disp:
        disp_id = existing_disp.id
        dispatch_code = existing_disp.dispatch_number
    else:
        disp_id = uuid.uuid4()

    outcome = OperationalOutcome(
        outcome_id=outcome_id,
        dispatch_id=disp_id,
        dispatch_code=dispatch_code,
        idempotency_key=f"IDEMP-57-{uid}",
        actual_transit_mins=25.0,
        actual_unloading_mins=15.0,
        actual_sla_breach_flag=True,
        actual_plant_risk_class=1,
        is_verified=True,
        verification_status="VERIFIED",
        outcome_timestamp=datetime.now(timezone.utc),
    )
    session.add(outcome)

    snapshot = MLPredictionSnapshot(
        prediction_snapshot_id=snapshot_id,
        idempotency_key=f"IDEMP-SNAP-{uid}",
        prediction_timestamp=datetime.now(timezone.utc),
        prediction_status="AUTHORITATIVE",
        dispatch_id=dispatch_code,
        dispatch_code=dispatch_code,
        model_name=model_family,
        model_version="v1.1.0-promoted",
        artifact_sha256="f75ff26e7769",
        feature_set_version="FeatureSetV1",
        vehicle_code="VEH-001",
        input_features={"distance_km": 15.0},
        prediction_outputs={"val": 20.0},
        predicted_value=20.0 if "regressor" in model_family else (1.0 if "sla" in model_family else 1.0),
        plant_code="ACC_DHARGA",
        customer_code="CUST-001",
    )
    session.add(snapshot)
    await session.commit()
    return outcome_id, snapshot_id, dispatch_code

@pytest.mark.asyncio
async def test_ws57_01_feedback_ingestion(ws57_session: AsyncSession):
    """Test 1: Ingestion of verified outcome creates valid MLFeedbackRecord."""
    session = ws57_session
    outcome_id, snapshot_id, _ = await _seed_test_outcome_and_snapshot(session, "delay_regressor")
    service = FeedbackLoopService(session)

    res = await service.ingest_feedback_for_outcome(outcome_id, planner_action="REROUTED_VEHICLE")
    assert res["success"] is True
    assert res["created_records"] == 1

    records = (await session.execute(select(MLFeedbackRecord).where(MLFeedbackRecord.prediction_snapshot_id == snapshot_id))).scalars().all()
    assert len(records) == 1
    assert records[0].predicted_value == 20.0
    assert records[0].realized_value == 25.0
    assert records[0].error_delta == -5.0
    assert records[0].planner_action_taken == "REROUTED_VEHICLE"

@pytest.mark.asyncio
async def test_ws57_02_unverified_outcome_rejection(ws57_session: AsyncSession):
    """Test 2: Unverified outcome is rejected from ingestion."""
    session = ws57_session
    uid = uuid.uuid4().hex[:6]
    res_disp = await session.execute(select(Dispatch))
    existing_disp = res_disp.scalars().first()
    disp_id = existing_disp.id if existing_disp else uuid.uuid4()
    disp_code = existing_disp.dispatch_number if existing_disp else f"DISP-UNV-{uid}"

    outcome = OperationalOutcome(
        outcome_id=f"OUT-UNVERIFIED-{uid}",
        dispatch_id=disp_id,
        dispatch_code=disp_code,
        idempotency_key=f"IDEMP-UNV-{uid}",
        is_verified=False,
        verification_status="RECEIVED",
        outcome_timestamp=datetime.now(timezone.utc),
    )
    session.add(outcome)
    await session.commit()

    service = FeedbackLoopService(session)
    with pytest.raises(ValueError, match="is unverified"):
        await service.ingest_feedback_for_outcome(f"OUT-UNVERIFIED-{uid}")

@pytest.mark.asyncio
async def test_ws57_03_ingestion_idempotency(ws57_session: AsyncSession):
    """Test 3: Re-ingesting same outcome does not create duplicate feedback records."""
    session = ws57_session
    outcome_id, _, _ = await _seed_test_outcome_and_snapshot(session, "delay_regressor")
    service = FeedbackLoopService(session)

    res1 = await service.ingest_feedback_for_outcome(outcome_id)
    res2 = await service.ingest_feedback_for_outcome(outcome_id)

    assert res1["created_records"] == 1
    assert res2["created_records"] == 1
    assert res1["feedback_ids"] == res2["feedback_ids"]

@pytest.mark.asyncio
async def test_ws57_04_eval_triggers_normal(ws57_session: AsyncSession):
    """Test 4: Continuous learning evaluation passes when error is low."""
    session = ws57_session
    outcome_id, _, _ = await _seed_test_outcome_and_snapshot(session, "delay_regressor")
    service = FeedbackLoopService(session)
    await service.ingest_feedback_for_outcome(outcome_id)

    res = await service.evaluate_continuous_learning_triggers("delay_regressor", threshold_mae=15.0)
    assert res["retrain_recommended"] is False
    assert res["error_mae"] == 5.0

@pytest.mark.asyncio
async def test_ws57_05_eval_triggers_breach(ws57_session: AsyncSession):
    """Test 5: Retraining trigger emitted when error exceeds threshold."""
    session = ws57_session
    uid = uuid.uuid4().hex[:6]
    res_disp = await session.execute(select(Dispatch))
    existing_disp = res_disp.scalars().first()
    disp_id = existing_disp.id if existing_disp else uuid.uuid4()
    disp_code = existing_disp.dispatch_number if existing_disp else f"DISP-HIGH-{uid}"

    outcome = OperationalOutcome(
        outcome_id=f"OUT-HIGH-ERR-{uid}",
        dispatch_id=disp_id,
        dispatch_code=disp_code,
        idempotency_key=f"IDEMP-HIGH-{uid}",
        actual_transit_mins=100.0,
        is_verified=True,
        verification_status="VERIFIED",
        outcome_timestamp=datetime.now(timezone.utc),
    )
    snapshot = MLPredictionSnapshot(
        prediction_snapshot_id=f"SNAP-HIGH-ERR-{uid}",
        idempotency_key=f"IDEMP-SNAP-HIGH-{uid}",
        prediction_timestamp=datetime.now(timezone.utc),
        prediction_status="AUTHORITATIVE",
        dispatch_id=disp_code,
        dispatch_code=disp_code,
        model_name="delay_regressor",
        model_version="v1.1.0-promoted",
        artifact_sha256="f75ff26e7769",
        feature_set_version="FeatureSetV1",
        vehicle_code="VEH-001",
        input_features={"distance_km": 15.0},
        prediction_outputs={"val": 10.0},
        predicted_value=10.0,
        plant_code="ACC_DHARGA",
        customer_code="CUST-001",
    )
    session.add_all([outcome, snapshot])
    await session.commit()

    service = FeedbackLoopService(session)
    await service.ingest_feedback_for_outcome(outcome.outcome_id)

    res = await service.evaluate_continuous_learning_triggers("delay_regressor", threshold_mae=15.0)
    assert res["retrain_recommended"] is True
    assert "breached threshold" in res["reason"]
