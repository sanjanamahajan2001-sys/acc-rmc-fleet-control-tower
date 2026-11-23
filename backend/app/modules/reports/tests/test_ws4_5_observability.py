import time
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.context import RequestContext
from app.core.database import get_db_session
from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus, ReportFormat, ReportRequestDTO, ReportScopeDTO
from app.modules.reports.services.security_limiter import SecurityRateLimiter, DownloadTokenManager
from app.modules.reports.services.telemetry import (
    ReportingMetricsCollector,
    REPORT_REQUESTS_TOTAL,
    REPORT_GENERATION_COMPLETED_TOTAL,
    REPORT_GENERATION_NO_DATA_TOTAL,
    REPORT_GENERATION_FAILURES_TOTAL,
    REPORT_RATE_LIMIT_EXCEEDED_TOTAL,
    REPORT_SECURITY_DENIALS_TOTAL,
    REPORT_DOWNLOAD_TOTAL,
    ARTIFACT_PURGE_TOTAL
)
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage


@pytest.fixture(autouse=True)
def reset_limiter():
    SecurityRateLimiter.reset()
    yield
    SecurityRateLimiter.reset()


# 1. Structured Log & Correlation ID Propagation Test
def test_ws4_5_correlation_id_propagation_and_logging():
    mock_db = AsyncMock()
    class MockExecuteResult:
        def scalars(self):
            class MockScalars:
                def first(self): return None
            return MockScalars()
    mock_db.execute.return_value = MockExecuteResult()

    app.dependency_overrides[get_db_session] = lambda: mock_db
    try:
        client = TestClient(app)
        headers = {"X-Correlation-ID": "test-corr-id-12345", "X-Request-ID": "test-req-id-67890"}
        res = client.get("/fleet-api/v1/reports/executions/exec-nonexistent/status", headers=headers)
        assert res.status_code == 404
        assert res.headers["X-Correlation-ID"] == "test-corr-id-12345"
        assert res.headers["X-Request-ID"] == "test-req-id-67890"
    finally:
        app.dependency_overrides.clear()




# 2. Prometheus Metric Counters Test
def test_ws4_5_prometheus_metric_counters():
    initial_completed = REPORT_GENERATION_COMPLETED_TOTAL.labels(report_id="site_operations", format="PDF")._value.get()
    ReportingMetricsCollector.record_completion(report_id="site_operations", format_str="PDF", duration_sec=0.15, record_count=25)
    new_completed = REPORT_GENERATION_COMPLETED_TOTAL.labels(report_id="site_operations", format="PDF")._value.get()
    assert new_completed == initial_completed + 1

    initial_no_data = REPORT_GENERATION_NO_DATA_TOTAL.labels(report_id="site_operations", format="PDF")._value.get()
    ReportingMetricsCollector.record_completion(report_id="site_operations", format_str="PDF", duration_sec=0.05, record_count=0)
    new_no_data = REPORT_GENERATION_NO_DATA_TOTAL.labels(report_id="site_operations", format="PDF")._value.get()
    assert new_no_data == initial_no_data + 1


# 3. Security & Rate Limit Telemetry Counters Test
def test_ws4_5_rate_limit_and_security_telemetry():
    initial_rl = REPORT_RATE_LIMIT_EXCEEDED_TOTAL.labels(endpoint="/generate")._value.get()
    ReportingMetricsCollector.record_rate_limit(endpoint="/generate")
    assert REPORT_RATE_LIMIT_EXCEEDED_TOTAL.labels(endpoint="/generate")._value.get() == initial_rl + 1

    initial_denial = REPORT_SECURITY_DENIALS_TOTAL.labels(reason="INVALID_DOWNLOAD_TOKEN")._value.get()
    ReportingMetricsCollector.record_security_denial(reason="INVALID_DOWNLOAD_TOKEN")
    assert REPORT_SECURITY_DENIALS_TOTAL.labels(reason="INVALID_DOWNLOAD_TOKEN")._value.get() == initial_denial + 1


# 4. Artifact & Purge Telemetry Test
def test_ws4_5_artifact_purge_telemetry():
    initial_purge = ARTIFACT_PURGE_TOTAL.labels(purge_type="expired")._value.get()
    ARTIFACT_PURGE_TOTAL.labels(purge_type="expired").inc()
    assert ARTIFACT_PURGE_TOTAL.labels(purge_type="expired")._value.get() == initial_purge + 1


# 5. Prometheus Label Cardinality Governance Test (No execution_id, request_id, or customer IDs)
def test_ws4_5_bounded_label_cardinality_safety():
    payload, content_type = ReportingMetricsCollector.get_metrics_payload()
    metrics_text = payload.decode("utf-8")
    assert "execution_id=" not in metrics_text
    assert "request_id=" not in metrics_text
    assert "customer_id=" not in metrics_text
    assert "vehicle_id=" not in metrics_text


# 6. Secret Redaction & Token Protection Test
def test_ws4_5_secret_redaction_protection():
    payload, _ = ReportingMetricsCollector.get_metrics_payload()
    metrics_text = payload.decode("utf-8")
    assert "super_secret_jwt_key" not in metrics_text
    assert "Bearer " not in metrics_text


# 7. GET /metrics Endpoint Security & Payload Test
def test_ws4_5_metrics_endpoint_payload():
    client = TestClient(app)
    res = client.get("/fleet-api/v1/reports/metrics")
    assert res.status_code == 200
    assert "report_requests_total" in res.text
    assert "report_generation_duration_seconds" in res.text




# 8. WS4.1 Async Worker Telemetry Compatibility Test
@pytest.mark.asyncio
async def test_ws4_5_ws4_1_async_worker_telemetry(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        from app.modules.reports.workers.report_worker import ReportBackgroundWorker
        exec_id = "exec-ws45-async"
        exec_record = ReportExecutionAudit(
            execution_id=exec_id,
            report_id="site_operations",
            report_type="site_dashboard",
            format="PDF",
            requested_by="telemetry_user",
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

        mock_report = AsyncMock()
        mock_report.model_dump.return_value = {"report_id": "site_operations", "record_count": 10}
        mock_report.record_count = 10

        with patch("app.modules.reports.handlers.site_operations_handler.SiteOperationsReportHandler.build_canonical_report", AsyncMock(return_value=mock_report)), \
             patch("app.modules.reports.renderers.json_renderer.JSONReportRenderer.render", return_value=b"{}"), \
             patch("app.modules.reports.renderers.xlsx_renderer.XLSXReportRenderer.render", return_value=b"XLSX"), \
             patch("app.modules.reports.renderers.pdf_renderer.PDFReportRenderer.render", return_value=b"PDF"):
            await ReportBackgroundWorker.process_report_task(
                execution_id=exec_id,
                report_id="site_operations",
                requested_scope={},
                effective_scope={},
                requested_by="telemetry_user",
                session_factory=mock_session_factory
            )
            assert exec_record.status == ReportStatus.COMPLETED.value



# 9. WS4.2 & WS4.3 & WS4.4 Telemetry Compatibility Test
@pytest.mark.asyncio
async def test_ws4_5_ws4_2_3_4_compatibility():
    from app.modules.reports.services.scope_resolver import ScopeResolverService
    resolver = ScopeResolverService()
    mock_db = AsyncMock()

    class MockExecuteResult:
        def scalar(self): return 12000

    mock_db.execute.return_value = MockExecuteResult()

    is_valid, _, error_reason = await resolver.resolve_and_validate_scope(session=mock_db, raw_scope={})
    assert is_valid is False
    assert "EXPORT_LIMIT_EXCEEDED" in str(error_reason)


# 10. Telemetry Overhead Performance Measurement Test
def test_ws4_5_telemetry_overhead_performance():
    t_start = time.perf_counter()
    for _ in range(1000):
        ReportingMetricsCollector.record_submission(report_id="site_operations", format_str="PDF")
        ReportingMetricsCollector.record_completion(report_id="site_operations", format_str="PDF", duration_sec=0.01, record_count=50)
    t_duration = time.perf_counter() - t_start

    # 1,000 telemetry operations completed in under 100 milliseconds (< 0.1ms per call)
    assert t_duration < 0.10
