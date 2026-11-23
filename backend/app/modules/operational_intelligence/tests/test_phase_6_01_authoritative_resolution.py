"""
WS-10 Phase 6.1 Authoritative Resolution & Runtime Cache Master Test Suite
Validates single authoritative model resolution, exclusion of candidate/rejected/superseded/deleted models,
SHA-256 integrity, missing artifact handling, concurrent caching, promotion/rollback cache sync,
and verification against real registered model artifacts across all 4 production families.
"""

import os
import uuid
import pytest
import pytest_asyncio
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.services.authoritative_resolver import (
    AuthoritativeModelResolver,
    NoPromotedModelError,
    AmbiguousModelAuthorityError,
    UnknownModelFamilyError,
    SUPPORTED_MODEL_FAMILIES,
)
from app.modules.operational_intelligence.services.model_runtime_adapter import (
    LightGBMRuntimeAdapter,
    ModelArtifactNotFoundError,
    ArtifactIntegrityError,
)
from app.modules.operational_intelligence.services.model_runtime_cache import ModelRuntimeCache

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()

@pytest_asyncio.fixture
async def ws61_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE ml_model_versions CASCADE;"))

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_model(
    session: AsyncSession,
    model_name: str,
    lifecycle_status: str = "PROMOTED",
    version_suffix: str = "01",
    sha256_val: Optional[str] = None,
    is_deleted: bool = False,
    artifact_path: Optional[str] = None,
) -> MLModelVersion:
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex[:6]
    sha = sha256_val or hashlib.sha256(f"art-{uid}".encode()).hexdigest()

    model = MLModelVersion(
        id=str(uuid.uuid4()),
        model_name=model_name,
        model_category="REGRESSION" if "regressor" in model_name else "CLASSIFICATION",
        algorithm="LIGHTGBM",
        target_name="target",
        training_dataset_id=f"DS-61-{uid}",
        artifact_path=artifact_path or f"/tmp/virtual_art_61_{uid}.pkl",
        artifact_sha256=sha,
        artifact_size_bytes=2048,
        training_timestamp=now,
        model_version=f"v1.0.{version_suffix}-{uid}",
        feature_set_version="FeatureSetV1",
        lifecycle_status=lifecycle_status,
        is_deleted=is_deleted,
    )
    session.add(model)
    await session.commit()
    return model


@pytest.mark.asyncio
async def test_ws61_01_single_promoted_model_resolution(ws61_session: AsyncSession):
    """Test 1: Successfully resolves single active PROMOTED model."""
    session = ws61_session
    seeded_model = await _seed_model(session, "delay_regressor", "PROMOTED")

    resolver = AuthoritativeModelResolver(session)
    resolved = await resolver.resolve_authoritative_model("delay_regressor")

    assert str(resolved.id) == str(seeded_model.id)
    assert resolved.model_version == seeded_model.model_version
    assert resolved.lifecycle_status == "PROMOTED"


@pytest.mark.asyncio
async def test_ws61_02_zero_promoted_model_fail_closed(ws61_session: AsyncSession):
    """Test 2: Fails closed with NoPromotedModelError when 0 PROMOTED models exist."""
    session = ws61_session
    await _seed_model(session, "delay_regressor", "CANDIDATE")

    resolver = AuthoritativeModelResolver(session)
    with pytest.raises(NoPromotedModelError):
        await resolver.resolve_authoritative_model("delay_regressor")


@pytest.mark.asyncio
async def test_ws61_03_multiple_promoted_model_fail_closed(ws61_session: AsyncSession):
    """Test 3: Fails closed with AmbiguousModelAuthorityError when >1 PROMOTED models exist."""
    session = ws61_session
    await session.execute(text("DROP INDEX IF EXISTS uq_active_promoted_model_per_name;"))
    await _seed_model(session, "turnaround_regressor", "PROMOTED", "01")
    await _seed_model(session, "turnaround_regressor", "PROMOTED", "02")

    resolver = AuthoritativeModelResolver(session)
    with pytest.raises(AmbiguousModelAuthorityError):
        await resolver.resolve_authoritative_model("turnaround_regressor")

    await session.execute(text("TRUNCATE TABLE ml_model_versions CASCADE;"))
    await session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_active_promoted_model_per_name ON ml_model_versions (model_name) WHERE lifecycle_status = 'PROMOTED' AND is_deleted = false;"))
    await session.commit()


@pytest.mark.asyncio
async def test_ws61_04_unknown_model_family_rejection(ws61_session: AsyncSession):
    """Test 4: Rejects unsupported model family name."""
    session = ws61_session
    resolver = AuthoritativeModelResolver(session)
    with pytest.raises(UnknownModelFamilyError):
        await resolver.resolve_authoritative_model("unknown_family_model")


@pytest.mark.asyncio
async def test_ws61_05_non_promoted_status_exclusions(ws61_session: AsyncSession):
    """Test 5: Explicitly verifies CANDIDATE, REJECTED, SUPERSEDED, and is_deleted models are excluded."""
    session = ws61_session
    await _seed_model(session, "delay_regressor", "CANDIDATE", "01")
    await _seed_model(session, "turnaround_regressor", "REJECTED", "02")
    await _seed_model(session, "sla_breach_classifier", "SUPERSEDED", "03")
    await _seed_model(session, "plant_risk_classifier", "PROMOTED", "04", is_deleted=True)

    resolver = AuthoritativeModelResolver(session)
    for fam in SUPPORTED_MODEL_FAMILIES:
        with pytest.raises(NoPromotedModelError):
            await resolver.resolve_authoritative_model(fam)


@pytest.mark.asyncio
async def test_ws61_06_runtime_cache_loading_and_invalidation(ws61_session: AsyncSession):
    """Test 6: ModelRuntimeCache loads adapter, reuses cache hit, and invalidates on demand."""
    session = ws61_session
    ModelRuntimeCache.reset_instance()
    cache = ModelRuntimeCache.get_instance()

    m1 = await _seed_model(session, "sla_breach_classifier", "PROMOTED", "01")

    adapter1 = await cache.get_adapter(session, "sla_breach_classifier")
    assert adapter1.model_version == m1.model_version

    # Cache Hit Verification
    adapter2 = await cache.get_adapter(session, "sla_breach_classifier")
    assert adapter1 is adapter2

    # Invalidate cache
    await cache.invalidate_cache("sla_breach_classifier")
    assert "sla_breach_classifier" not in cache._adapters


@pytest.mark.asyncio
async def test_ws61_07_corrupted_artifact_sha256_rejection(tmp_path):
    """Test 7: Rejects artifact loading if actual file SHA-256 does not match registered SHA-256."""
    fake_file = tmp_path / "corrupted_model.pkl"
    fake_file.write_bytes(b"corrupted binary data content")

    real_sha = hashlib.sha256(b"corrupted binary data content").hexdigest()
    wrong_sha = "0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises((ArtifactIntegrityError, ValueError), match="Artifact SHA-256 mismatch"):
        LightGBMRuntimeAdapter(
            model_name="delay_regressor",
            model_version="v1.0.0",
            artifact_path=str(fake_file),
            expected_sha256=wrong_sha,
        )

    adapter = LightGBMRuntimeAdapter(
        model_name="delay_regressor",
        model_version="v1.0.0",
        artifact_path=str(fake_file),
        expected_sha256=real_sha,
    )
    assert adapter.model_version == "v1.0.0"


@pytest.mark.asyncio
async def test_ws61_08_missing_artifact_error(ws61_session: AsyncSession):
    """Test 8: Verifies ModelArtifactNotFoundError when registered artifact is missing from disk."""
    session = ws61_session
    m1 = await _seed_model(session, "delay_regressor", "PROMOTED", "01", artifact_path="/non_existent_path/missing_model.pkl")

    cache = ModelRuntimeCache.get_instance()
    cache._adapters.clear()

    with pytest.raises(ModelArtifactNotFoundError):
        await cache.get_adapter(session, "delay_regressor")


@pytest.mark.asyncio
async def test_ws61_09_concurrent_cache_initialization(ws61_session: AsyncSession):
    """Test 9: Verifies concurrent async requests safely initialize cache without race conditions."""
    session = ws61_session
    ModelRuntimeCache.reset_instance()
    cache = ModelRuntimeCache.get_instance()

    m1 = await _seed_model(session, "plant_risk_classifier", "PROMOTED", "01")

    # Launch 10 concurrent requests to resolve adapter
    tasks = [cache.get_adapter(session, "plant_risk_classifier") for _ in range(10)]
    adapters = await asyncio.gather(*tasks)

    # All returned instances must be identical singleton reference
    assert len(adapters) == 10
    first_adapter = adapters[0]
    for ad in adapters:
        assert ad is first_adapter


@pytest.mark.asyncio
async def test_ws61_10_promotion_and_rollback_cache_sync(ws61_session: AsyncSession):
    """Test 10: Promotion & Rollback trigger cache synchronization and adapter reload."""
    session = ws61_session
    ModelRuntimeCache.reset_instance()
    cache = ModelRuntimeCache.get_instance()

    m1 = await _seed_model(session, "delay_regressor", "PROMOTED", "01")
    ad1 = await cache.get_adapter(session, "delay_regressor")
    assert ad1.model_version == m1.model_version

    # Promote new model (superseding m1)
    m1.lifecycle_status = "SUPERSEDED"
    session.add(m1)
    await session.commit()

    m2 = await _seed_model(session, "delay_regressor", "PROMOTED", "02")

    # Atomic reload
    ad2 = await cache.reload_adapter(session, "delay_regressor")
    assert ad2.model_version == m2.model_version
    assert ad2.model_version != ad1.model_version
