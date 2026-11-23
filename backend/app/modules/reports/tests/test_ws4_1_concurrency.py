import time
import asyncio
import io
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db_session
from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat

from app.modules.reports.workers.report_worker import ReportBackgroundWorker
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage


# 1. Async Submission & Initial QUEUED State Test
@pytest.mark.asyncio
async def test_ws4_1_async_submission_and_queued_state():
    from app.modules.reports.api.router import generate_report_async
    from app.modules.reports.schemas.report_schemas import ReportRequestDTO, ReportScopeDTO

    mock_db = AsyncMock()
    real_exec = ReportExecutionAudit(
        execution_id="exec-ws41-queued-1",
        report_id="site_operations",
        report_type="site_dashboard",
        format="PDF",
        requested_by="test_user",
        requested_at=datetime.now(timezone.utc),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05"},
        scope_fingerprint="fp-ws41-queued",
        scope_validation_status="VALIDATED",
        record_count=10,
        dataset_id="DS-20260805-VASCO",
        status="QUEUED"
    )

    req = ReportRequestDTO(
        report_id="site_operations",
        format=ReportFormat.PDF,
        requested_by="test_user",
        scope=ReportScopeDTO(plant_id="VASCO", operation_date="2026-08-05")
    )
    mock_bg = AsyncMock()

    with patch("app.modules.reports.api.router.report_service.create_execution_record", AsyncMock(return_value=real_exec)), \
         patch("app.modules.reports.api.router.scope_resolver.resolve_and_validate_scope", AsyncMock(return_value=(True, {"plant_id": "VASCO", "operation_date": "2026-08-05"}, None))):

        res = await generate_report_async(req=req, background_tasks=mock_bg, db=mock_db)
        assert res.execution_id == "exec-ws41-queued-1"
        assert res.status == ReportStatus.QUEUED




# 2. Worker Execution & State Machine Transition (QUEUED -> PROCESSING -> COMPLETED)
@pytest.mark.asyncio
async def test_ws4_1_worker_state_machine_transition():
    mock_db = AsyncMock()
    mock_exec = AsyncMock()
    mock_exec.execution_id = "exec-ws41-trans-1"
    mock_exec.status = "QUEUED"
    mock_exec.scope_fingerprint = "fp-trans-1"
    mock_exec.record_count = 10
    mock_db.get.return_value = mock_exec

    class MockSessionFactory:
        def __call__(self):
            class AsyncContext:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncContext()

    mock_report = AsyncMock()
    mock_report.record_count = 10

    with patch("app.modules.reports.workers.report_worker.site_operations_handler.build_canonical_report", AsyncMock(return_value=mock_report)), \
         patch("app.modules.reports.workers.report_worker.JSONReportRenderer.render", return_value=b'{"test": 1}'), \
         patch("app.modules.reports.workers.report_worker.XLSXReportRenderer.render", return_value=b'PK123'), \
         patch("app.modules.reports.workers.report_worker.PDFReportRenderer.render", return_value=b'%PDF-1.4'), \
         patch("app.modules.reports.workers.report_worker.ReportArtifactStorage.save_artifacts") as mock_save:

        await ReportBackgroundWorker.process_report_task(
            execution_id="exec-ws41-trans-1",
            report_id="site_operations",
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            requested_by="test_user",
            session_factory=MockSessionFactory()
        )

        assert mock_exec.status == "COMPLETED"
        assert mock_save.called


# 3. Worker State Machine Transition for Empty Scope (QUEUED -> PROCESSING -> NO_DATA)
@pytest.mark.asyncio
async def test_ws4_1_worker_no_data_transition():
    mock_db = AsyncMock()
    mock_exec = AsyncMock()
    mock_exec.execution_id = "exec-ws41-nodata-1"
    mock_exec.status = "QUEUED"
    mock_exec.scope_fingerprint = "fp-nodata-1"
    mock_exec.record_count = 0
    mock_db.get.return_value = mock_exec

    class MockSessionFactory:
        def __call__(self):
            class AsyncContext:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncContext()

    mock_report = AsyncMock()
    mock_report.record_count = 0

    with patch("app.modules.reports.workers.report_worker.site_operations_handler.build_canonical_report", AsyncMock(return_value=mock_report)), \
         patch("app.modules.reports.workers.report_worker.JSONReportRenderer.render", return_value=b'{"test": 0}'), \
         patch("app.modules.reports.workers.report_worker.XLSXReportRenderer.render", return_value=b'PK123'), \
         patch("app.modules.reports.workers.report_worker.PDFReportRenderer.render", return_value=b'%PDF-1.4'), \
         patch("app.modules.reports.workers.report_worker.ReportArtifactStorage.save_artifacts"):

        await ReportBackgroundWorker.process_report_task(
            execution_id="exec-ws41-nodata-1",
            report_id="site_operations",
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            requested_by="test_user",
            session_factory=MockSessionFactory()
        )

        assert mock_exec.status == "NO_DATA"


# 4. Failure Recovery Transition (QUEUED -> PROCESSING -> FAILED)
@pytest.mark.asyncio
async def test_ws4_1_failure_recovery_transition():
    mock_db = AsyncMock()
    mock_exec = AsyncMock()
    mock_exec.execution_id = "exec-ws41-fail-1"
    mock_exec.status = "QUEUED"
    mock_exec.scope_fingerprint = "fp-fail-1"
    mock_db.get.return_value = mock_exec

    class MockSessionFactory:
        def __call__(self):
            class AsyncContext:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncContext()

    with patch("app.modules.reports.workers.report_worker.site_operations_handler.build_canonical_report", side_effect=RuntimeError("DB Connection Error")):
        await ReportBackgroundWorker.process_report_task(
            execution_id="exec-ws41-fail-1",
            report_id="site_operations",
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            requested_by="test_user",
            session_factory=MockSessionFactory()
        )

        assert mock_exec.status == "FAILED"
        assert mock_exec.error_code == "REPORT_GENERATION_FAILED"


# 5. Idempotency & Duplicate Task Protection Test
@pytest.mark.asyncio
async def test_ws4_1_idempotency_duplicate_task_protection():
    mock_db = AsyncMock()
    mock_exec = AsyncMock()
    mock_exec.execution_id = "exec-ws41-completed-already"
    mock_exec.status = "COMPLETED"
    mock_db.get.return_value = mock_exec

    class MockSessionFactory:
        def __call__(self):
            class AsyncContext:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncContext()

    with patch("app.modules.reports.workers.report_worker.site_operations_handler.build_canonical_report") as mock_build:
        await ReportBackgroundWorker.process_report_task(
            execution_id="exec-ws41-completed-already",
            report_id="site_operations",
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            requested_by="test_user",
            session_factory=MockSessionFactory()
        )

        assert not mock_build.called
        assert mock_exec.status == "COMPLETED"


# 6. Status Polling Endpoint Test
def test_ws4_1_status_polling_endpoint():
    real_exec = ReportExecutionAudit(
        execution_id="exec-ws41-poll-1",
        report_id="site_operations",
        report_type="site_dashboard",
        format="PDF",
        requested_by="test_user",
        requested_at=datetime.now(timezone.utc),
        requested_scope={"plant_id": "VASCO"},
        effective_scope={"plant_id": "VASCO"},
        scope_fingerprint="fp-poll",
        scope_validation_status="VALIDATED",
        record_count=5,
        dataset_id="DS-20260805-VASCO",
        status="PROCESSING"
    )

    class MockExecuteResult:
        def scalars(self):
            class MockScalars:
                def first(self): return real_exec
            return MockScalars()


    mock_session = AsyncMock()
    mock_session.execute.return_value = MockExecuteResult()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        client = TestClient(app)
        res = client.get("/fleet-api/v1/reports/executions/exec-ws41-poll-1/status")
        assert res.status_code == 200
        data = res.json()
        assert data["execution_id"] == "exec-ws41-poll-1"
        assert data["status"] == "PROCESSING"
    finally:
        app.dependency_overrides.clear()


# 7. Concurrent Execution Latency Measurement Test
@pytest.mark.asyncio
async def test_ws4_1_concurrency_latency_benchmark():
    mock_db = AsyncMock()
    mock_exec = AsyncMock()
    mock_exec.execution_id = "exec-ws41-bench"
    mock_exec.status = "QUEUED"
    mock_exec.scope_fingerprint = "fp-bench"
    mock_exec.record_count = 1
    mock_db.get.return_value = mock_exec

    class MockSessionFactory:
        def __call__(self):
            class AsyncContext:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncContext()

    mock_report = AsyncMock()
    mock_report.record_count = 1

    with patch("app.modules.reports.workers.report_worker.site_operations_handler.build_canonical_report", AsyncMock(return_value=mock_report)), \
         patch("app.modules.reports.workers.report_worker.JSONReportRenderer.render", return_value=b'{"bench": 1}'), \
         patch("app.modules.reports.workers.report_worker.XLSXReportRenderer.render", return_value=b'PK123'), \
         patch("app.modules.reports.workers.report_worker.PDFReportRenderer.render", return_value=b'%PDF-1.4'), \
         patch("app.modules.reports.workers.report_worker.ReportArtifactStorage.save_artifacts"):

        t0 = time.perf_counter()
        tasks = [
            ReportBackgroundWorker.process_report_task(
                execution_id=f"exec-ws41-bench-{i}",
                report_id="site_operations",
                requested_scope={"plant_id": "VASCO"},
                effective_scope={"plant_id": "VASCO"},
                requested_by="test_user",
                session_factory=MockSessionFactory()
            )
            for i in range(10)
        ]
        await asyncio.gather(*tasks)
        t1 = time.perf_counter()

        elapsed_ms = (t1 - t0) * 1000
        print(f"BENCHMARK_WS4_1_CONCURRENCY: 10_TASKS_ELAPSED_MS={elapsed_ms:.2f}")
        assert elapsed_ms < 5000.0
