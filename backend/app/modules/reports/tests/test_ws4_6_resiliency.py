import os
import time
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus, ReportFormat, ReportRequestDTO, ReportScopeDTO
from app.modules.reports.services.security_limiter import SecurityRateLimiter, DownloadTokenManager
from app.modules.reports.services.resilience import (
    ReportCircuitBreaker,
    CircuitState,
    db_circuit_breaker,
    execute_with_resilience,
    REPORT_CIRCUIT_BREAKER_OPEN_TOTAL
)
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage
from app.modules.reports.workers.report_worker import ReportBackgroundWorker



@pytest.fixture(autouse=True)
def reset_cb():
    db_circuit_breaker.reset()
    yield
    db_circuit_breaker.reset()


# 1. Circuit Breaker State Transitions (CLOSED ➔ OPEN ➔ HALF_OPEN ➔ CLOSED)
@pytest.mark.asyncio
async def test_ws4_6_circuit_breaker_state_transitions():
    cb = ReportCircuitBreaker(dependency_name="test_db", failure_threshold=2, cooldown_seconds=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_execution() is True

    # First failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # Second failure triggers OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_execution() is False

    # Wait for cooldown
    await asyncio.sleep(0.12)
    assert cb.allow_execution() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Successful probe restores CLOSED state
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


# 2. Circuit Breaker HALF_OPEN Probe Failure
@pytest.mark.asyncio
async def test_ws4_6_circuit_breaker_half_open_failure():
    cb = ReportCircuitBreaker(dependency_name="test_db_2", failure_threshold=1, cooldown_seconds=0.05)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.06)
    assert cb.allow_execution() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Failed probe returns immediately to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


# 3. Resilience Execution Bounded Retry & Backoff
@pytest.mark.asyncio
async def test_ws4_6_execute_with_resilience_retry_and_exhaustion():
    call_count = 0

    async def transient_failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("Transient DB Disconnection")
        return "SUCCESS"

    res = await execute_with_resilience(transient_failing_func, operation_name="test_transient", max_retries=2, initial_delay_sec=0.01)
    assert res == "SUCCESS"
    assert call_count == 2

    # Non-retryable error test (ValueError should not retry)
    val_err_count = 0
    async def val_error_func():
        nonlocal val_err_count
        val_err_count += 1
        raise ValueError("Invalid Parameter")

    with pytest.raises(ValueError):
        await execute_with_resilience(val_error_func, operation_name="test_val", max_retries=2, initial_delay_sec=0.01)
    assert val_err_count == 1  # No retries executed for ValueError


# 4. Background Worker Failure Recovery (PROCESSING ➔ FAILED)
@pytest.mark.asyncio
async def test_ws4_6_worker_failure_recovery_no_stuck_processing(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        exec_id = "exec-resilience-fail"
        exec_record = ReportExecutionAudit(
            execution_id=exec_id,
            report_id="site_operations",
            report_type="site_dashboard",
            format="PDF",
            requested_by="resilience_user",
            requested_scope={},
            effective_scope={},
            scope_fingerprint="fp1",
            scope_validation_status="VALIDATED",
            record_count=10,
            status="QUEUED"
        )

        mock_db = AsyncMock()
        mock_db.get.return_value = exec_record

        def mock_session_factory():
            class AsyncSessionContextManager:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncSessionContextManager()

        with patch("app.modules.reports.handlers.site_operations_handler.SiteOperationsReportHandler.build_canonical_report", side_effect=RuntimeError("Database Connection Timeout")):
            await ReportBackgroundWorker.process_report_task(
                execution_id=exec_id,
                report_id="site_operations",
                requested_scope={},
                effective_scope={},
                requested_by="resilience_user",
                session_factory=mock_session_factory
            )

            # Execution state transitioned out of PROCESSING to FAILED safely
            assert exec_record.status == ReportStatus.FAILED.value
            assert exec_record.error_code == "REPORT_GENERATION_FAILED"


# 5. NO_DATA vs Infrastructure Failure Distinction Test
@pytest.mark.asyncio
async def test_ws4_6_no_data_vs_infrastructure_failure_distinction(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        exec_id = "exec-resilience-nodata"
        exec_record = ReportExecutionAudit(
            execution_id=exec_id,
            report_id="site_operations",
            report_type="site_dashboard",
            format="PDF",
            requested_by="nodata_user",
            requested_scope={},
            effective_scope={},
            scope_fingerprint="fp1",
            scope_validation_status="VALIDATED",
            record_count=0,
            status="QUEUED"
        )

        mock_db = AsyncMock()
        mock_db.get.return_value = exec_record

        def mock_session_factory():
            class AsyncSessionContextManager:
                async def __aenter__(self): return mock_db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return AsyncSessionContextManager()

        mock_report = AsyncMock()
        mock_report.model_dump.return_value = {"report_id": "site_operations", "record_count": 0}
        mock_report.record_count = 0

        with patch("app.modules.reports.handlers.site_operations_handler.SiteOperationsReportHandler.build_canonical_report", AsyncMock(return_value=mock_report)), \
             patch("app.modules.reports.renderers.json_renderer.JSONReportRenderer.render", return_value=b"{}"), \
             patch("app.modules.reports.renderers.xlsx_renderer.XLSXReportRenderer.render", return_value=b"XLSX"), \
             patch("app.modules.reports.renderers.pdf_renderer.PDFReportRenderer.render", return_value=b"PDF"):

            await ReportBackgroundWorker.process_report_task(
                execution_id=exec_id,
                report_id="site_operations",
                requested_scope={},
                effective_scope={},
                requested_by="nodata_user",
                session_factory=mock_session_factory
            )

            # Legitimate query return 0 records -> NO_DATA, not FAILED
            assert exec_record.status == ReportStatus.NO_DATA.value


# 6. Failed Execution Partial Artifact Cleanup Test
def test_ws4_6_failed_execution_artifact_cleanup(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        exec_id = "exec-partial-clean"
        ReportArtifactStorage.save_artifacts(exec_id, {"pdf": b"PARTIAL_CONTENT"})
        assert os.path.exists(ReportArtifactStorage.get_artifact_path(exec_id, "pdf"))

        # Trigger purge upon failure
        ReportArtifactStorage.purge_execution_artifacts(exec_id)

        with pytest.raises(FileNotFoundError):
            ReportArtifactStorage.get_artifact_path(exec_id, "pdf")


# 7. WS4.1 Async & WS4.2 Record Boundary Compatibility Test
@pytest.mark.asyncio
async def test_ws4_6_ws4_1_and_ws4_2_compatibility():
    from app.modules.reports.services.scope_resolver import ScopeResolverService
    resolver = ScopeResolverService()
    mock_db = AsyncMock()

    class MockExecuteResult:
        def scalar(self): return 15000

    mock_db.execute.return_value = MockExecuteResult()

    is_valid, _, error_reason = await resolver.resolve_and_validate_scope(session=mock_db, raw_scope={})
    assert is_valid is False
    assert "EXPORT_LIMIT_EXCEEDED" in str(error_reason)


# 8. WS4.3 Storage Retention & Traversal Compatibility Test
def test_ws4_6_ws4_3_retention_and_traversal_compatibility(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        with pytest.raises(ValueError):
            ReportArtifactStorage.save_artifacts("../../../etc/passwd", {"pdf": b"BAD"})


# 9. WS4.4 Rate Limiting & Security Compatibility Test
def test_ws4_6_ws4_4_security_compatibility():
    token = DownloadTokenManager.create_download_token(
        execution_id="exec-ws46-sec",
        user_id="sec_user",
        format_ext="pdf"
    )
    assert DownloadTokenManager.verify_download_token(token, "exec-ws46-sec", "pdf", "sec_user") is True


# 10. WS4.5 Telemetry Compatibility & Metric Recording Test
def test_ws4_6_ws4_5_telemetry_recording():
    initial_open = REPORT_CIRCUIT_BREAKER_OPEN_TOTAL.labels(dependency="test_metric_dep")._value.get()
    cb = ReportCircuitBreaker(dependency_name="test_metric_dep", failure_threshold=1)
    cb.record_failure()
    assert REPORT_CIRCUIT_BREAKER_OPEN_TOTAL.labels(dependency="test_metric_dep")._value.get() == initial_open + 1
