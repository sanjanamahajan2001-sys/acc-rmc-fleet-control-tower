import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.operational_intelligence_canonical import CanonicalOperationalIntelligenceReport, ReportMetadataDTO, OperationalIntelligenceKPISummary
from app.modules.reports.handlers.operational_intelligence_handler import OperationalIntelligenceReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import SiteReadinessResponseDTO, SiteReadinessDTO, OperationalIntelligenceStatusEnum, OperationalGradeEnum

mock_dto = SiteReadinessResponseDTO(
    success=True,
    status=OperationalIntelligenceStatusEnum.AVAILABLE,
    total_sites=10,
    data=[
        SiteReadinessDTO(
            site_id=f"SITE-{i:02d}",
            site_name=f"Site Location {i}",
            rank=i,
            total_trips=100 - i * 5,
            swi_site=95.0 - i,
            dpi_site=90.0 - i,
            fui_site=85.0 - i,
            sri_score=90.0 - i,
            grade=OperationalGradeEnum.GRADE_A if i <= 3 else OperationalGradeEnum.GRADE_B
        )
        for i in range(1, 11)
    ],
    filters={"plant_id": "ALL", "operation_date": "2026-08-05"}
)

handler = OperationalIntelligenceReportHandler()
raw_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"}

t0 = time.perf_counter()
with patch("app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness.SiteReadinessEngine.get_site_readiness", return_value=mock_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-opint-10", raw_scope, eff_scope, "fp-bench-opint"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_5_OPERATIONAL_INTELLIGENCE:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
