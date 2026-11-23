import time
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

from app.modules.reports.schemas.erp_import_audit_canonical import CanonicalERPImportAuditReport, ReportMetadataDTO, ERPImportAuditKPISummary, ERPImportJobRecord
from app.modules.reports.handlers.erp_import_audit_handler import ERPImportAuditReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.erp.models import ImportJob

job_uuid = uuid4()
mock_job = ImportJob(
    id=job_uuid,
    job_number="JOB-20260805-ABCD1234",
    status="COMPLETED",
    file_name="dispatch_data_20260805.xlsx",
    file_hash="a" * 64,
    total_rows=100,
    processed_rows=100,
    error_count=0,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc)
)

class MockExecuteResult:
    def scalars(self):
        class MockScalars:
            def all(self): return [mock_job]
        return MockScalars()

mock_session = AsyncMock()
mock_session.execute.return_value = MockExecuteResult()

handler = ERPImportAuditReportHandler()
raw_scope = {"operation_date": "2026-08-05"}
eff_scope = {"operation_date": "2026-08-05", "resolved_dataset_id": "DS-20260805-GLOBAL"}

t0 = time.perf_counter()
report = asyncio.run(handler.build_canonical_report(mock_session, "bench-erp-1", raw_scope, eff_scope, "fp-bench-erp"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_10_ERP_IMPORT_AUDIT:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
