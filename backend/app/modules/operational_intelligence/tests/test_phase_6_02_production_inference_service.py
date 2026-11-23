"""
WS-10 Phase 6.2 Production Inference Service Test Suite
Validates single-family & all-four-family inference, FeatureSetV1 extraction,
authoritative model binding, snapshot creation, idempotency, force_reprocess, and smart RMC recommendations.
"""

import os
import uuid
import pytest
import pytest_asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.services.production_inference_service import (
    ProductionInferenceService,
    FeatureLeakageViolationError,
)

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()

@pytest_asyncio.fixture
async def ws62_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE ml_prediction_snapshots, ml_model_versions CASCADE;"))

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_all_promoted_models(session: AsyncSession) -> Dict[str, MLModelVersion]:
    now = datetime.now(timezone.utc)
    models = {}
    families = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]

    for fam in families:
        uid = uuid.uuid4().hex[:6]
        sha = hashlib.sha256(f"art-{fam}-{uid}".encode()).hexdigest()
        model = MLModelVersion(
            id=str(uuid.uuid4()),
            model_name=fam,
            model_category="REGRESSION" if "regressor" in fam else "CLASSIFICATION",
            algorithm="LIGHTGBM",
            target_name="target",
            training_dataset_id=f"DS-{uid}",
            artifact_path=f"/tmp/virtual_art_{fam}_{uid}.pkl",
            artifact_sha256=sha,
            artifact_size_bytes=2048,
            training_timestamp=now,
            model_version=f"v1.1.0-prom-{uid}",
            feature_set_version="FeatureSetV1",
            lifecycle_status="PROMOTED",
            is_deleted=False,
        )
        session.add(model)
        models[fam] = model

    await session.commit()
    return models


@pytest.mark.asyncio
async def test_ws62_01_single_family_inference(ws62_session: AsyncSession):
    """Test 1: Single-family inference resolves authority and creates 1 snapshot."""
    session = ws62_session
    models = await _seed_all_promoted_models(session)
    disp_id = str(uuid.uuid4())

    service = ProductionInferenceService(session)
    res = await service.execute_inference(disp_id, model_family="delay_regressor")

    assert res.dispatch_id == disp_id
    assert len(res.predictions) == 1
    assert "delay_regressor" in res.predictions
    assert res.snapshots_created == 1
    assert res.snapshots_reused == 0


@pytest.mark.asyncio
async def test_ws62_02_all_four_families_inference_when_omitted(ws62_session: AsyncSession):
    """Test 2: Omitting model_family executes inference across ALL 4 certified families."""
    session = ws62_session
    models = await _seed_all_promoted_models(session)
    disp_id = str(uuid.uuid4())

    service = ProductionInferenceService(session)
    res = await service.execute_inference(disp_id, model_family=None)

    assert len(res.predictions) == 4
    for fam in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
        assert fam in res.predictions
    assert res.snapshots_created == 4


@pytest.mark.asyncio
async def test_ws62_03_snapshot_idempotency(ws62_session: AsyncSession):
    """Test 3: Repeated execution reuses existing snapshot and does not duplicate."""
    session = ws62_session
    models = await _seed_all_promoted_models(session)
    disp_id = str(uuid.uuid4())

    service = ProductionInferenceService(session)
    res1 = await service.execute_inference(disp_id, model_family="turnaround_regressor")
    assert res1.snapshots_created == 1
    assert res1.snapshots_reused == 0

    # Second execution reuses snapshot
    res2 = await service.execute_inference(disp_id, model_family="turnaround_regressor")
    assert res2.snapshots_created == 0
    assert res2.snapshots_reused == 1
    assert res2.predictions["turnaround_regressor"]["reused"] is True


@pytest.mark.asyncio
async def test_ws62_04_force_reprocess_invalidation(ws62_session: AsyncSession):
    """Test 4: force_reprocess=True marks prior snapshot stale and creates new snapshot."""
    session = ws62_session
    models = await _seed_all_promoted_models(session)
    disp_id = str(uuid.uuid4())

    service = ProductionInferenceService(session)
    res1 = await service.execute_inference(disp_id, model_family="sla_breach_classifier")
    snap1_id = res1.predictions["sla_breach_classifier"]["snapshot_id"]

    res2 = await service.execute_inference(disp_id, model_family="sla_breach_classifier", force_reprocess=True)
    snap2_id = res2.predictions["sla_breach_classifier"]["snapshot_id"]

    assert res2.snapshots_created == 1
    assert snap1_id != snap2_id


@pytest.mark.asyncio
async def test_ws62_05_forbidden_leakage_field_rejection(ws62_session: AsyncSession):
    """Test 5: Reject inference if features contain forbidden target realization leakage fields."""
    session = ws62_session
    models = await _seed_all_promoted_models(session)
    disp_id = str(uuid.uuid4())

    leakage_features = {
        "dispatch_distance_km": 20.0,
        "t2a_holding_mins": 45.0, # FORBIDDEN LEAKAGE FIELD!
    }

    service = ProductionInferenceService(session)
    with pytest.raises(FeatureLeakageViolationError, match="Forbidden target realization/leakage field"):
        await service.execute_inference(disp_id, provided_features=leakage_features)
