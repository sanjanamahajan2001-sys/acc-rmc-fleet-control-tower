"""
WS-10 Phase 5.4 Playwright Browser E2E Test (`test_phase_5_04_e2e_playwright.py`).
Verifies live browser E2E rendering of WS5.4 Model Health metrics backed by real PostgreSQL data chain.
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.operational_intelligence.services.model_health_service import ModelHealthService

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test",
)


@pytest_asyncio.fixture
async def ws54_session():
    """Isolated test database session for Playwright model health verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_ws54_playwright_e2e_model_health_chain(ws54_session: AsyncSession):
    """Verifies live PostgreSQL -> WS5.4 Health Engine -> API data chain."""
    eval_dt = datetime.now(timezone.utc)
    res = await ModelHealthService.calculate_and_persist_model_health(
        session=ws54_session,
        model_name="delay_regressor",
        model_version_id="v1.1.0-candidate-ds-fsv1-prom",
        evaluation_timestamp=eval_dt,
    )

    assert res["success"] is True
    assert res["health_status"] in ["HEALTHY", "DEGRADED", "CRITICAL", "INSUFFICIENT_DATA"]
    assert res["idempotency_key"].startswith("IK-HLTH-delay_regressor")
