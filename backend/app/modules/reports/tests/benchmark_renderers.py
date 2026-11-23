import time
from app.modules.reports.schemas.dispatch_analysis_canonical import (
    CanonicalDispatchAnalysisReport, ReportMetadataDTO, DispatchAnalysisKPIs, DispatchAnalysisRecord
)
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer

records = [
    DispatchAnalysisRecord(
        dispatch_id=f"d{i}",
        dispatch_number=f"DISP-{i:04d}",
        dispatch_date="2026-08-05",
        time_out="08:00",
        time_in="08:45",
        plant_code="VASCO",
        customer_code="C001",
        customer_name="Benchmark Customer",
        vehicle_id=f"V-{i:03d}",
        driver_name="Benchmark Driver",
        interval_mins=15.0,
        variance_mins=0.0,
        holding_mins=10.0,
        retention_mins=5.0,
        sla_status="COMPLIANT",
        trip_status="COMPLETED",
        cadence_recommendation="MAINTAIN"
    ) for i in range(1, 101)
]

report = CanonicalDispatchAnalysisReport(
    metadata=ReportMetadataDTO(execution_id="bench-100", report_id="dispatch_analysis", requested_by="bench_user"),
    requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05"},
    effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "resolved_dataset_id": "DS-20260805-VASCO"},
    scope_fingerprint="bench-fp-12345",
    status="COMPLETED",
    record_count=100,
    kpis=DispatchAnalysisKPIs(total_dispatches=100, completed_dispatches=100),
    records=records
)

t0 = time.perf_counter()
json_bytes = JSONReportRenderer.render(report)
t1 = time.perf_counter()
xlsx_bytes = XLSXReportRenderer.render(report)
t2 = time.perf_counter()
pdf_bytes = PDFReportRenderer.render(report)
t3 = time.perf_counter()

print("BENCHMARK_100_RECORDS:")
print(f"JSON_MS={((t1-t0)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t2-t1)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t3-t2)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t3-t0)*1000):.2f}")
