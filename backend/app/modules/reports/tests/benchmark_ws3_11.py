import time
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.erp_data_explorer_canonical import CanonicalERPDataExplorerReport, ReportMetadataDTO, ERPDataExplorerKPISummary, ERPDispatchRecord
from app.modules.reports.handlers.erp_data_explorer_handler import ERPDataExplorerReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer

disp_uuid = uuid4()
mock_dispatch_dict = {
    "id": disp_uuid,
    "dispatch_number": "DN-EXP-001",
    "plant_name": "VASCO Batch Plant",
    "customer_name": "L&T Construction",
    "vehicle_code": "GA-01-A-1234",
    "status": "COMPLETED",
    "telemetry_status": "CORRELATED",
    "correlation_score": "0.98",
    "time_out": datetime.now(timezone.utc),
    "time_in": datetime.now(timezone.utc),
    "cycle_time": 45.0
}

class MockExecuteResult:
    def scalar_one(self): return 1

mock_session = AsyncMock()
mock_session.execute.return_value = MockExecuteResult()

handler = ERPDataExplorerReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.reports.handlers.erp_data_explorer_handler._generic_explorer_query", AsyncMock(return_value=([mock_dispatch_dict], 1))):
    report = asyncio.run(handler.build_canonical_report(mock_session, "bench-exp-1", raw_scope, eff_scope, "fp-bench-exp"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_11_ERP_DATA_EXPLORER:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
