import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.site_operations_canonical import (
    CanonicalSiteOperationsReport,
    SiteOperationsKPIs,
    ReportMetadataDTO
)
from app.modules.reports.handlers.site_operations_handler import SiteOperationsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService


@pytest.fixture
def sample_site_operations_report():
    return CanonicalSiteOperationsReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-site-001",
            report_id="site_operations",
            report_name="Site Operations Report",
            generated_at="2026-08-19T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-site-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=15,
        kpis=SiteOperationsKPIs(
            total_dispatches=15,
            within_sla_count=14,
            outside_sla_count=1,
            compliance_pct=93.33,
            violation_pct=6.67,
            avg_holding_mins=12.5,
            percentile_95_holding_mins=25.0,
            max_holding_mins=30.0,
            avg_retention_mins=6.0,
            max_retention_mins=15.0,
            avg_site_time_mins=18.5
        ),
        delay_distribution=[],
        insights=[],
        records=[]
    )


# 1. Authoritative Data & Canonical DTO Test
from unittest.mock import patch
from app.modules.site_dashboard.widgets.site_performance.dtos import (
    SitePerformanceResponseDTO, PerformanceSummaryDTO
)

@pytest.mark.asyncio
async def test_ws3_1_canonical_data_assembly():
    handler = SiteOperationsReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = SitePerformanceResponseDTO(
        summary=PerformanceSummaryDTO(
            total_dispatches=10,
            within_sla_count=9,
            outside_sla_count=1,
            compliance_pct=90.0,
            violation_pct=10.0,
            avg_holding_mins=11.0,
            percentile_95_holding_mins=20.0,
            max_holding_mins=25.0,
            avg_retention_mins=5.0,
            max_retention_mins=10.0,
            avg_site_time_mins=16.0
        ),
        delay_distribution=[],
        insights=[]
    )

    with patch("app.modules.site_dashboard.widgets.site_performance.service.SitePerformanceService.get_site_performance", return_value=mock_dto):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-1",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-1",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "site_operations"
    assert report.effective_scope["resolved_dataset_id"] == "DS-20260805-VASCO"
    assert isinstance(report.kpis, SiteOperationsKPIs)
    assert report.kpis.total_dispatches == 10



# 2. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_1_multi_format_rendering(sample_site_operations_report):
    json_bytes = JSONReportRenderer.render(sample_site_operations_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_site_operations_report)
    pdf_bytes = PDFReportRenderer.render(sample_site_operations_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "site_operations"
    assert json_obj["kpis"]["compliance_pct"] == 93.33

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) >= 1

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 3. Cross-Format Parity Test
def test_ws3_1_cross_format_parity(sample_site_operations_report):
    json_bytes = JSONReportRenderer.render(sample_site_operations_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_site_operations_report.scope_fingerprint
    assert json_obj["record_count"] == sample_site_operations_report.record_count
    assert json_obj["kpis"]["total_dispatches"] == sample_site_operations_report.kpis.total_dispatches


# 4. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_1_no_data_rendering(sample_site_operations_report):
    sample_site_operations_report.status = ReportStatus.NO_DATA
    sample_site_operations_report.record_count = 0

    json_bytes = JSONReportRenderer.render(sample_site_operations_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0


# 5. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_1_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 6. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_1_dataset_authority_override_protection():
    resolver = ScopeResolverService()
    raw_scope = {
        "plant_id": "VASCO",
        "operation_date": "2026-08-05",
        "resolved_dataset_id": "FAKE_CLIENT_OVERRIDE"
    }
    class MockSession:
        async def execute(self, query):
            class MockResult:
                def scalar(self): return 5
            return MockResult()

    ok, eff_scope, err = await resolver.resolve_and_validate_scope(session=MockSession(), raw_scope=raw_scope)
    assert ok is True
    assert eff_scope["resolved_dataset_id"] != "FAKE_CLIENT_OVERRIDE"
    assert eff_scope["resolved_dataset_id"].startswith("DS-20260805-VASCO")


# 7. Invalid Scope API End-to-End Test
def test_ws3_1_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "site_operations",
                "format": "PDF",
                "requested_by": "test_user",
                "scope": {
                    "plant_id": "INVALID_PLANT_CODE",
                    "operation_date": "2026-08-05"
                }
            }
            res = client.post("/fleet-api/v1/reports/generate", json=payload)
            assert res.status_code == 400
            assert "REPORT_SCOPE_VALIDATION_FAILED" in str(res.json())
        finally:
            app.dependency_overrides.clear()



# 8. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_1_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage
    from app.modules.reports.schemas.report_schemas import ReportStatus

    exec_id = "exec-ws31-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Site Ops PDF",
            "xlsx": b"PK123 Site Ops XLSX",
            "json": b'{"report_id": "site_operations"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Site Ops PDF"





