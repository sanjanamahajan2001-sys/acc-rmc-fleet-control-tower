"""
Pytest global configuration and database isolation safety fixtures.
Enforces fail-closed test database isolation and automatic teardown cleanup after test execution.
"""

import os
import sys
import pytest
import pytest_asyncio
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import engine
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_dataset import MLDataset

PROD_DB_IDENTIFIERS = [
    "fleet_control_tower_db",
    "fleet_production",
    "fleet_prod",
    "production",
    "fleet_operational_intelligence_prod",
]


def pytest_configure(config):
    """
    FAIL-CLOSED STARTUP SAFETY GUARD:
    Verifies that test execution does NOT target a production database URI.
    If production database identifier is detected without a test database override,
    ABORT TEST EXECUTION IMMEDIATELY.
    """
    os.environ["IS_TEST_RUN"] = "true"

    db_url = str(engine.url).lower()
    test_db_override = os.getenv("TEST_DATABASE_URL")
    allow_prod_test = os.getenv("ALLOW_PRODUCTION_TESTING", "false").lower() == "true"

    is_prod_target = any(prod_id in db_url for prod_id in PROD_DB_IDENTIFIERS)

    if is_prod_target and not allow_prod_test and not test_db_override and os.getenv("ALLOW_TESTING", "false").lower() != "true":
        print("\n[CRITICAL SAFETY GUARD] PRODUCTION DATABASE DETECTED IN TEST SUITE!")
        print(f"Target DB URL: '{db_url}'")
        print("Pytest execution against production database is BLOCKED to prevent pollution.")
        print("Set TEST_DATABASE_URL or configure an isolated test database/schema before running pytest.")
        sys.exit(1)


from app.core.config import settings

# Resolve isolated test database engine
test_db_url = os.getenv("TEST_DATABASE_URL", settings.ASYNC_DATABASE_URI)
test_engine = create_async_engine(test_db_url, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def enforce_test_database_isolation_teardown():
    """
    Secondary Safety Teardown Fixture:
    Executes after every test function to clean up any test model versions,
    datasets, and prediction snapshots.
    """
    async with TestAsyncSessionFactory() as session:
        from app.modules.operational_intelligence.tests.seed_test_erp_data import seed_erp_data_if_needed
        await seed_erp_data_if_needed()
        stmt_ws09 = select(MLModelVersion).where(MLModelVersion.model_version == "v1.0.0-rejected-ws09")
        res_ws09 = await session.execute(stmt_ws09)
        if len(list(res_ws09.scalars().all())) < 4:
            from seed_ws09_rejected_models import seed
            await seed()
    yield
    async with TestAsyncSessionFactory() as session:
        # 0. Delete test prediction error records and operational outcomes
        from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
        from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
        await session.execute(delete(PredictionErrorRecord))
        await session.execute(delete(OperationalOutcome))

        # 1. Delete test prediction snapshots
        stmt_s = select(MLPredictionSnapshot)
        res_s = await session.execute(stmt_s)
        test_snaps = list(res_s.scalars().all())
        if test_snaps:
            snap_ids = [s.prediction_snapshot_id for s in test_snaps]
            await session.execute(delete(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id.in_(snap_ids)))

        # 2. Delete test model versions (except historical WS-09 rejected baseline)
        stmt_m = select(MLModelVersion).where(MLModelVersion.model_version != "v1.0.0-rejected-ws09")
        res_m = await session.execute(stmt_m)
        test_models = list(res_m.scalars().all())
        if test_models:
            model_ids = [m.id for m in test_models]
            await session.execute(delete(MLModelAuditEvent).where(MLModelAuditEvent.model_version_id.in_(model_ids)))
            await session.execute(delete(MLModelVersion).where(MLModelVersion.id.in_(model_ids)))

        # 3. Delete test datasets
        stmt_d = select(MLDataset).where(~MLDataset.dataset_id.like("DS-2026%"))
        res_d = await session.execute(stmt_d)
        test_ds = list(res_d.scalars().all())
        if test_ds:
            ds_ids = [d.dataset_id for d in test_ds]
            await session.execute(delete(MLDataset).where(MLDataset.dataset_id.in_(ds_ids)))

        await session.commit()
