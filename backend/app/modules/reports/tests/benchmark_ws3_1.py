import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.site_operations_canonical import CanonicalSiteOperationsReport, ReportMetadataDTO, SiteOperationsKPIs
from app.modules.reports.handlers.site_operations_handler import SiteOperationsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.site_dashboard.widgets.site_performance.dtos import SitePerformanceResponseDTO, PerformanceSummaryDTO

mock_dto = SitePerformanceResponseDTO(
    summary=PerformanceSummaryDTO(
        total_dispatches=100,
        within_sla_count=90,
        outside_sla_count=10,
        compliance_pct=90.0,
        violation_pct=10.0,
        avg_holding_mins=12.0,
        percentile_95_holding_mins=22.0,
        max_holding_mins=28.0,
        avg_retention_mins=6.0,
        max_retention_mins=14.0,
        avg_site_time_mins=18.0
    ),
    delay_distribution=[],
    insights=[]
)

handler = SiteOperationsReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.site_dashboard.widgets.site_performance.service.SitePerformanceService.get_site_performance", return_value=mock_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-site-100", raw_scope, eff_scope, "fp-bench"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_1_SITE_OPERATIONS:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
