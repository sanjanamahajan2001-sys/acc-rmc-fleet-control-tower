import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.site_comparison_canonical import CanonicalSiteComparisonReport, ReportMetadataDTO, SiteComparisonKPISummary
from app.modules.reports.handlers.site_comparison_handler import SiteComparisonReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import SiteComparisonResponseDTO, SiteComparisonDTO, OperationalIntelligenceStatusEnum

mock_dto = SiteComparisonResponseDTO(
    success=True,
    status=OperationalIntelligenceStatusEnum.AVAILABLE,
    data=[
        SiteComparisonDTO(
            rank=i,
            site_code=f"SITE-{i:02d}",
            site_name=f"Site Location {i}",
            dispatches=50 - i,
            volume_cum=300.0 - i * 5,
            avg_holding_mins=10.0 + i,
            avg_retention_mins=5.0 + i * 0.5,
            max_queue_tms=4,
            dispatch_accuracy=98.0 - i,
            status="Optimal" if i <= 5 else "Good"
        )
        for i in range(1, 11)
    ],
    filters={"plant_id": "ALL", "operation_date": "2026-08-05"}
)

handler = SiteComparisonReportHandler()
raw_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"}

t0 = time.perf_counter()
with patch("app.modules.operational_dashboard.widgets.operational_intelligence.services.site_comparison.SiteComparisonEngine.get_site_comparison", return_value=mock_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-comp-10", raw_scope, eff_scope, "fp-bench-comp"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_3_SITE_COMPARISON:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
