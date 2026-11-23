import time
import asyncio
import io
import json
import psutil
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ReportFormat
from app.modules.reports.schemas.dispatch_analysis_canonical import (
    CanonicalDispatchAnalysisReport,
    ReportMetadataDTO,
    DispatchAnalysisKPIs,
    DispatchAnalysisRecord
)
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService


def generate_synthetic_dispatch_report(record_count: int) -> CanonicalDispatchAnalysisReport:
    records = [
        DispatchAnalysisRecord(
            dispatch_id=f"DISP-{i:05d}",
            dispatch_number=f"DN-{i:05d}",
            dispatch_date="2026-08-05T08:00:00Z",
            time_out="2026-08-05T08:00:00Z",
            time_in="2026-08-05T08:45:00Z",
            plant_code="VASCO",
            customer_code="CUST-001",
            customer_name="L&T Construction",
            vehicle_id="GA-01-A-1234",
            driver_name="Driver One",
            interval_mins=15.0,
            variance_mins=0.0,
            holding_mins=10.0,
            retention_mins=5.0,
            sla_status="ON_TIME",
            trip_status="COMPLETED",
            cadence_recommendation="MAINTAIN"
        )
        for i in range(record_count)
    ]

    return CanonicalDispatchAnalysisReport(
        metadata=ReportMetadataDTO(
            execution_id=f"exec-bench-{record_count}",
            report_id="dispatch_analysis",
            report_name="Dispatch Analysis Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="bench_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint=f"fp-bench-{record_count}",
        status=ReportStatus.COMPLETED,
        record_count=record_count,
        kpis=DispatchAnalysisKPIs(
            total_dispatches=record_count,
            on_schedule_dispatches=record_count,
            sla_compliance_pct=100.0,
            avg_interval_mins=15.0,
            interval_variance_mins=0.0,
            das_score_pct=95.0,
            completed_dispatches=record_count,
            avg_loading_mins=10.0,
            avg_transit_mins=20.0,
            recommended_interval_mins=15.0,
            cadence_status="OPTIMAL",
            potential_delay_reduction_hrs=0.0
        ),
        records=records,
        delay_categories=[],
        insights=[]
    )


# 1. Benchmark 1,000 Records Render & Memory Test
def test_ws4_2_benchmark_1000_records():
    proc = psutil.Process()
    mem_before = proc.memory_info().rss / (1024 * 1024)

    report = generate_synthetic_dispatch_report(1000)

    t0 = time.perf_counter()
    json_b = JSONReportRenderer.render(report)
    t1 = time.perf_counter()
    xlsx_b = XLSXReportRenderer.render(report)
    t2 = time.perf_counter()
    pdf_b = PDFReportRenderer.render(report)
    t3 = time.perf_counter()

    mem_after = proc.memory_info().rss / (1024 * 1024)
    mem_diff = mem_after - mem_before

    print(f"\nBENCHMARK_1000_RECORDS: JSON_MS={((t1-t0)*1000):.2f}, XLSX_MS={((t2-t1)*1000):.2f}, PDF_MS={((t3-t2)*1000):.2f}, MEM_DIFF_MB={mem_diff:.2f}, XLSX_SIZE_KB={len(xlsx_b)/1024:.2f}")

    assert len(json_b) > 0
    assert len(xlsx_b) > 0
    assert len(pdf_b) > 0


# 2. Benchmark 5,000 Records Render & Memory Test
def test_ws4_2_benchmark_5000_records():
    proc = psutil.Process()
    mem_before = proc.memory_info().rss / (1024 * 1024)

    report = generate_synthetic_dispatch_report(5000)

    t0 = time.perf_counter()
    json_b = JSONReportRenderer.render(report)
    t1 = time.perf_counter()
    xlsx_b = XLSXReportRenderer.render(report)
    t2 = time.perf_counter()

    mem_after = proc.memory_info().rss / (1024 * 1024)
    mem_diff = mem_after - mem_before

    print(f"\nBENCHMARK_5000_RECORDS: JSON_MS={((t1-t0)*1000):.2f}, XLSX_MS={((t2-t1)*1000):.2f}, MEM_DIFF_MB={mem_diff:.2f}, XLSX_SIZE_KB={len(xlsx_b)/1024:.2f}")

    assert len(json_b) > 0
    assert len(xlsx_b) > 0


# 3. Benchmark 10,000 Records Render & Memory Test
def test_ws4_2_benchmark_10000_records():
    proc = psutil.Process()
    mem_before = proc.memory_info().rss / (1024 * 1024)

    report = generate_synthetic_dispatch_report(10000)

    t0 = time.perf_counter()
    json_b = JSONReportRenderer.render(report)
    t1 = time.perf_counter()
    xlsx_b = XLSXReportRenderer.render(report)
    t2 = time.perf_counter()

    mem_after = proc.memory_info().rss / (1024 * 1024)
    mem_diff = mem_after - mem_before

    print(f"\nBENCHMARK_10000_RECORDS: JSON_MS={((t1-t0)*1000):.2f}, XLSX_MS={((t2-t1)*1000):.2f}, MEM_DIFF_MB={mem_diff:.2f}, XLSX_SIZE_KB={len(xlsx_b)/1024:.2f}")

    assert len(json_b) > 0
    assert len(xlsx_b) > 0


# 4. Resource Boundary & Scope Governance Test (Rejects > 10,000 records)
@pytest.mark.asyncio
async def test_ws4_2_resource_boundary_scope_governance():
    resolver = ScopeResolverService()
    mock_session = AsyncMock()

    class MockExecuteResult:
        def scalar(self): return 15000  # Exceeds 10,000 ceiling

    mock_session.execute.return_value = MockExecuteResult()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05"}
    is_valid, eff_scope, error_reason = await resolver.resolve_and_validate_scope(session=mock_session, raw_scope=raw_scope)

    assert is_valid is False
    assert "EXPORT_LIMIT_EXCEEDED" in str(error_reason)


# 5. Artifact Integrity Test
def test_ws4_2_artifact_integrity():
    report = generate_synthetic_dispatch_report(100)
    json_b = JSONReportRenderer.render(report)
    json_obj = json.loads(json_b.decode("utf-8"))

    assert json_obj["record_count"] == 100
    assert len(json_obj["records"]) == 100
    assert json_obj["records"][0]["dispatch_id"] == "DISP-00000"
