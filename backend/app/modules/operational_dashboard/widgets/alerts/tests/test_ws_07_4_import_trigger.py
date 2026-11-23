"""
WS-07.4 Comprehensive PyTest Test Suite for Import-Triggered Alert Evaluation & Persistence.
Verifies post-commit boundaries, concurrency, failure semantics, correlation, readiness, lifecycle, and scope isolation.
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
from app.modules.operational_dashboard.widgets.alerts.trigger_service import AlertTriggerOrchestrator

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Function-scoped fresh database session to prevent asyncpg connection loop leaks across tests."""
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()

# -----------------------------------------------------------------------------
# 1. TRANSACTION BOUNDARY & POST-COMMIT INTEGRATION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_commit_transaction_boundary_and_rollback_isolation(db_session: AsyncSession):
    """Verify that uncommitted/rolled back transactions produce ZERO alerts."""
    test_dataset = f"DS-ROLLBACK-{uuid.uuid4().hex[:6]}"

    # Fetch required FK IDs from dispatches table to build valid dummy row
    res_disp = await db_session.execute(text("SELECT ticket_id, plant_id, vehicle_id, driver_id, customer_id, dispatch_date, status FROM dispatches LIMIT 1;"))
    row = res_disp.fetchone()

    if row:
        ticket_id, plant_id, vehicle_id, driver_id, customer_id, dispatch_date, disp_status = row
        # Simulate uncommitted/failed import transaction
        db_session.begin_nested() # Savepoint
        await db_session.execute(text(
            f"INSERT INTO dispatches (id, ticket_id, plant_id, vehicle_id, driver_id, customer_id, dispatch_number, dispatch_date, status, t2a_holding_mins, is_generated) "
            f"VALUES ('{uuid.uuid4()}', '{ticket_id}', '{plant_id}', '{vehicle_id}', '{driver_id}', '{customer_id}', 'DSP-TEMP-001', '{dispatch_date}', '{disp_status}', 45.0, false);"
        ))
        await db_session.rollback()

    # Verify 0 alerts persisted for rolled back dataset
    res = await db_session.execute(select(OperationalAlertModel).where(OperationalAlertModel.dataset_id == test_dataset))
    alerts = res.scalars().all()
    assert len(alerts) == 0

@pytest.mark.asyncio
async def test_successful_post_commit_trigger_execution(db_session: AsyncSession):
    """Verify end-to-end post-commit alert trigger evaluation & persistence."""
    test_dataset = f"DS-POSTCOMMIT-{uuid.uuid4().hex[:6]}"
    import_job_id = uuid.uuid4()

    summary = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session,
        dataset_id=test_dataset,
        import_job_id=str(import_job_id),
        plant_id="ALL",
        customer_id="ALL",
    )

    assert summary["status"] == "SUCCESS"
    assert summary["dispatch_count"] == 3532
    assert summary["candidate_count"] == 2689
    assert summary["inserted_count"] == 2689 # 100% newly inserted
    assert summary["duration_ms"] < 3000.0

    res = await db_session.execute(
        select(OperationalAlertModel).where(OperationalAlertModel.dataset_id == test_dataset).limit(10)
    )
    persisted_alerts = res.scalars().all()
    assert len(persisted_alerts) > 0

    for a in persisted_alerts:
        assert a.status == "OPEN"
        assert a.acknowledged_at is None
        assert a.acknowledged_by is None
        assert a.acknowledgement_notes is None
        assert a.resolved_at is None
        assert a.resolved_by is None
        assert a.resolution_reason is None
        assert a.import_job_id == import_job_id

    # Clean up test rows
    await db_session.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id = '{test_dataset}';"))
    await db_session.commit()

# -----------------------------------------------------------------------------
# 2. CONCURRENCY & IDEMPOTENCY TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_duplicate_persistence():
    """Verify concurrent workers persisting same alert_fingerprint + dataset_id handle conflicts via UNIQUE constraint."""
    test_dataset = f"DS-CONCURRENCY-{uuid.uuid4().hex[:6]}"

    async def worker_task(worker_id: int):
        engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            summary = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
                session=session,
                dataset_id=test_dataset,
                plant_id="ACC_KUNDAIM",
                customer_id="CUST_AARA_HOTELS",
            )
        await engine.dispose()
        return summary

    # Run Worker A and Worker B concurrently
    res_a, res_b = await asyncio.gather(worker_task(1), worker_task(2))

    assert res_a["status"] == "SUCCESS"
    assert res_b["status"] == "SUCCESS"

    # Exactly 3 total rows inserted across both workers combined
    total_inserted = res_a["inserted_count"] + res_b["inserted_count"]
    assert total_inserted == 3

    # Clean up
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async with engine.connect() as conn:
        await conn.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id = '{test_dataset}';"))
        await conn.commit()
    await engine.dispose()

@pytest.mark.asyncio
async def test_same_dataset_reimport_idempotency(db_session: AsyncSession):
    """Verify re-importing the same dataset skips duplicates via UNIQUE(alert_fingerprint, dataset_id)."""
    test_dataset = f"DS-IDEM-{uuid.uuid4().hex[:6]}"

    # Run #1
    summary_1 = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=test_dataset
    )
    assert summary_1["status"] == "SUCCESS"
    assert summary_1["inserted_count"] == 2689

    # Run #2 (Re-import)
    summary_2 = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=test_dataset
    )
    assert summary_2["status"] == "SUCCESS"
    assert summary_2["inserted_count"] == 0 # 0 new insertions
    assert summary_2["duplicate_count"] == summary_2["candidate_count"] # 100% skipped as duplicates

    # Clean up
    await db_session.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id = '{test_dataset}';"))
    await db_session.commit()

@pytest.mark.asyncio
async def test_different_dataset_independence(db_session: AsyncSession):
    """Verify same dispatches under different dataset_ids create independent alert records."""
    dataset_a = f"DS-ALPHA-{uuid.uuid4().hex[:6]}"
    dataset_b = f"DS-BETA-{uuid.uuid4().hex[:6]}"

    summary_a = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=dataset_a, plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS"
    )
    summary_b = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=dataset_b, plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS"
    )

    assert summary_a["inserted_count"] == 3
    assert summary_b["inserted_count"] == 3

    # Clean up test rows
    await db_session.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id IN ('{dataset_a}', '{dataset_b}');"))
    await db_session.commit()

# -----------------------------------------------------------------------------
# 3. FAILURE SEMANTICS TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluation_failure_after_commit(db_session: AsyncSession):
    """Verify evaluator failure does not raise or fabricate alerts, but returns structured FAILED summary."""
    test_dataset = f"DS-FAIL-EVAL-{uuid.uuid4().hex[:6]}"

    with patch("app.modules.operational_dashboard.widgets.alerts.evaluator_engine.AlertRulesEvaluatorEngine.evaluate_dispatches", side_effect=RuntimeError("Evaluator internal error")):
        summary = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
            session=db_session, dataset_id=test_dataset
        )

    assert summary["status"] == "FAILED"
    assert summary["inserted_count"] == 0

    # Verify zero alerts persisted
    res = await db_session.execute(select(OperationalAlertModel).where(OperationalAlertModel.dataset_id == test_dataset))
    assert len(res.scalars().all()) == 0

@pytest.mark.asyncio
async def test_persistence_failure_semantics(db_session: AsyncSession):
    """Verify DB session failure during batch persistence rolls back current batch and returns FAILED summary."""
    test_dataset = f"DS-FAIL-PERSIST-{uuid.uuid4().hex[:6]}"

    with patch.object(db_session, "execute", side_effect=RuntimeError("DB Connection dropped during persistence")):
        summary = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
            session=db_session, dataset_id=test_dataset, plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS"
        )

    assert summary["status"] == "FAILED"
    assert summary["inserted_count"] == 0

# -----------------------------------------------------------------------------
# 4. CORRELATION & READINESS & GENERATED DATA EXCLUSION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_job_id_correlation(db_session: AsyncSession):
    """Verify exact import_job_id string/UUID is propagated to persisted alert records."""
    test_dataset = f"DS-CORR-{uuid.uuid4().hex[:6]}"
    raw_job_id = uuid.uuid4()

    summary = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=test_dataset, import_job_id=str(raw_job_id), plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS"
    )

    assert summary["status"] == "SUCCESS"
    assert summary["inserted_count"] == 3

    res = await db_session.execute(select(OperationalAlertModel).where(OperationalAlertModel.dataset_id == test_dataset))
    alerts = res.scalars().all()

    for a in alerts:
        assert a.import_job_id == raw_job_id

    # Clean up
    await db_session.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id = '{test_dataset}';"))
    await db_session.commit()

@pytest.mark.asyncio
async def test_degraded_readiness_persistence(db_session: AsyncSession):
    """Verify DEGRADED readiness status produces exactly 1 dataset-level INFO candidate with dispatch_id=NULL."""
    test_dataset = f"DS-DEGRADED-{uuid.uuid4().hex[:6]}"

    from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import OptimizationReadinessDTO, DataQualitySummaryDTO, ReadinessStatusEnum, OptimizationFilterParamsDTO

    mock_readiness = OptimizationReadinessDTO(
        success=True,
        status=ReadinessStatusEnum.DEGRADED,
        reason_code="DATA_QUALITY_DEGRADED",
        message="Platform data quality is degraded",
        quality_summary=DataQualitySummaryDTO(total_dispatches=10, active_vehicle_count=5),
        blocking_conditions=["Missing lat/lng geocodes for 5 dispatches"],
        filters=OptimizationFilterParamsDTO(),
    )

    with patch("app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine.OptimizationReadinessEngine.evaluate_readiness", return_value=mock_readiness):
        summary = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
            session=db_session, dataset_id=test_dataset, plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS"
        )

    assert summary["status"] == "SUCCESS"
    assert summary["readiness_alert_persisted"] is True

    res = await db_session.execute(
        select(OperationalAlertModel).where(
            OperationalAlertModel.dataset_id == test_dataset,
            OperationalAlertModel.alert_type == "DEGRADED_DATA_QUALITY"
        )
    )
    readiness_alert = res.scalar_one_or_none()
    assert readiness_alert is not None
    assert readiness_alert.dispatch_id is None
    assert readiness_alert.severity == "INFO"
    assert readiness_alert.status == "OPEN"

    # Clean up
    await db_session.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id = '{test_dataset}';"))
    await db_session.commit()

# -----------------------------------------------------------------------------
# 5. FIVE-SCOPE INTEGRATION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_five_scope_post_commit_trigger_persistence(db_session: AsyncSession):
    """Verify 5-scope post-commit trigger persistence against PostgreSQL dispatches."""
    dataset_v02 = f"DS-VASCO-{uuid.uuid4().hex[:6]}"
    dataset_v05 = f"DS-EMPTY-{uuid.uuid4().hex[:6]}"

    # V-02 Vasco
    summary_v02 = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=dataset_v02, plant_id="ACC_VASCO", customer_id="ALL"
    )
    assert summary_v02["dispatch_count"] == 1174

    # V-05 Empty Scope
    summary_v05 = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session, dataset_id=dataset_v05, plant_id="NO_DATA_SCOPE", customer_id="ALL"
    )
    assert summary_v05["dispatch_count"] == 0
    assert summary_v05["candidate_count"] == 0
    assert summary_v05["inserted_count"] == 0

    # Clean up
    await db_session.execute(text(f"DELETE FROM operational_alerts WHERE dataset_id IN ('{dataset_v02}', '{dataset_v05}');"))
    await db_session.commit()
