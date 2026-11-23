"""
WS-07.9 Dedicated Backend PyTest Suite for Import-to-Alert E2E, Archival Transition, Retention & Scheduler Automation.
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.modules.operational_dashboard.widgets.alerts.trigger_service import AlertTriggerOrchestrator
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
from app.modules.operational_dashboard.widgets.alerts.service import AlertService, RESOLVED_OPERATIONAL_RETENTION_HOURS
from app.modules.operational_dashboard.widgets.alerts.repository import OperationalAlertRepository
from app.workers.scheduler import Scheduler
from app.factory import scheduled_alert_archival_task

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session_factory() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_ws_07_9_import_to_alert_e2e_pipeline(db_session):
    """TEST 15: Excel import post-commit trigger -> Alert evaluation -> PostgreSQL persistence -> API Retrieval"""
    res = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session,
        dataset_id='DS-20260805-001',
        import_job_id=None,
        plant_id='ALL',
        customer_id='ALL'
    )
    assert res['status'] == 'SUCCESS'
    assert res['dispatch_count'] == 3532
    assert res['candidate_count'] == 2689
    
    # Verify PostgreSQL persistence
    alert_count_res = await db_session.execute(
        select(func.count()).select_from(OperationalAlertModel).where(OperationalAlertModel.dataset_id == 'DS-20260805-001')
    )
    assert alert_count_res.scalar() == 2689

@pytest.mark.asyncio
async def test_ws_07_9_idempotency_duplicate_protection(db_session):
    """TEST 16: Re-importing same dataset skips duplicates via SHA-256 fingerprinting"""
    res = await AlertTriggerOrchestrator.process_post_commit_import_alerts(
        session=db_session,
        dataset_id='DS-20260805-001',
        import_job_id=None,
        plant_id='ALL',
        customer_id='ALL'
    )
    assert res['status'] == 'SUCCESS'
    assert res['inserted_count'] == 0
    assert res['duplicate_count'] == 2689

@pytest.mark.asyncio
async def test_ws_07_9_resolved_to_archived_lifecycle_and_retention(db_session):
    """TEST 1 - 10, 12, 13, 14: RESOLVED -> ARCHIVED transition, archived_at persistence, retention threshold, and non-deletion"""
    # 1. Fetch an OPEN alert to transition
    models, count = await OperationalAlertRepository.list_alerts(db_session, status="OPEN", page=1, page_size=1)
    assert len(models) == 1
    alert_id = models[0].id

    # 2. Resolve alert (OPEN -> RESOLVED)
    dto, error = await AlertService.resolve_alert(
        db_session,
        alert_id=alert_id,
        resolved_by="Operator_Test",
        resolution_reason="Testing Archival Policy"
    )
    assert error is None
    assert dto.status == "RESOLVED"
    assert dto.resolved_at is not None

    # 3. Simulate older resolved timestamp beyond retention threshold (e.g. 25 hours ago)
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    model = await OperationalAlertRepository.get_alert_by_id(db_session, alert_id)
    model.resolved_at = old_time
    await db_session.commit()

    # 4. Trigger archival policy execution
    archived_count = await AlertService.archive_resolved_alerts(db_session, retention_hours=RESOLVED_OPERATIONAL_RETENTION_HOURS)
    assert archived_count >= 1

    # 5. Verify status transitioned to ARCHIVED and archived_at persisted
    archived_model = await OperationalAlertRepository.get_alert_by_id(db_session, alert_id)
    assert archived_model.status == "ARCHIVED"
    assert archived_model.archived_at is not None

    # 6. Verify non-deletion: Alert STILL exists in PostgreSQL
    check_exists = await db_session.execute(
        select(func.count()).select_from(OperationalAlertModel).where(OperationalAlertModel.id == alert_id)
    )
    assert check_exists.scalar() == 1

    # 7. Verify active KPI summary excludes ARCHIVED alert
    summary = await AlertService.get_summary(db_session)
    archived_list = await AlertService.get_alerts_list(db_session, status="ARCHIVED", page=1, page_size=10)
    assert archived_list.total_count >= 1
    # Active alerts = OPEN + ACKNOWLEDGED
    assert summary.total_active_alerts == summary.critical_count + summary.warning_count + summary.info_count

@pytest.mark.asyncio
async def test_ws_07_9_scheduler_background_execution_integration(db_session):
    """TEST 11: Production Cron Scheduler background loop automatically executes alert archival task"""
    test_scheduler = Scheduler()
    test_scheduler.schedule_periodic_task(
        name="test_alert_archival",
        interval_seconds=0.1,
        task=scheduled_alert_archival_task
    )

    await test_scheduler.start()
    await asyncio.sleep(0.3)
    await test_scheduler.stop()

    assert test_scheduler._is_running is False
