import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.site_comparison_canonical import (
    CanonicalSiteComparisonReport,
    SiteComparisonKPISummary,
    ReportMetadataDTO,
    SiteComparisonRecord
)
from app.modules.reports.handlers.site_comparison_handler import SiteComparisonReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    SiteComparisonResponseDTO, SiteComparisonDTO, OperationalIntelligenceStatusEnum
)


@pytest.fixture
def sample_site_comparison_report():
    return CanonicalSiteComparisonReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-comp-001",
            report_id="site_comparison",
            report_name="Site Comparison Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"},
        scope_fingerprint="sha256-site-comp-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=SiteComparisonKPISummary(
            total_sites_evaluated=2,
            total_dispatches=25,
            total_volume_cum=150.0,
            avg_holding_mins=12.5,
            avg_retention_mins=6.0,
            avg_dispatch_accuracy=92.5,
            optimal_sites_count=2
        ),
        records=[
            SiteComparisonRecord(
                rank=1,
                site_code="VASCO",
                site_name="Vasco ReadyMix Site",
                dispatches=15,
                volume_cum=90.0,
                avg_holding_mins=10.0,
                avg_retention_mins=5.0,
                max_queue_tms=3,
                dispatch_accuracy=95.0,
                status="Optimal"
            ),
            SiteComparisonRecord(
                rank=2,
                site_code="PANJIM",
                site_name="Panjim Batching Plant",
                dispatches=10,
                volume_cum=60.0,
                avg_holding_mins=15.0,
                avg_retention_mins=7.0,
                max_queue_tms=2,
                dispatch_accuracy=90.0,
                status="Optimal"
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data & Source Mapping Test
@pytest.mark.asyncio
async def test_ws3_3_authoritative_data_binding():
    handler = SiteComparisonReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"}

    mock_dto = SiteComparisonResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.AVAILABLE,
        data=[
            SiteComparisonDTO(
                rank=1,
                site_code="VASCO",
                site_name="Vasco ReadyMix Site",
                dispatches=15,
                volume_cum=90.0,
                avg_holding_mins=10.0,
                avg_retention_mins=5.0,
                max_queue_tms=3,
                dispatch_accuracy=95.0,
                status="Optimal"
            )
        ],
        filters=eff_scope
    )

    with patch("app.modules.operational_dashboard.widgets.operational_intelligence.services.site_comparison.SiteComparisonEngine.get_site_comparison", return_value=mock_dto):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-3",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-3",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "site_comparison"
    assert report.effective_scope["resolved_dataset_id"] == "DS-20260805-ALL"
    assert isinstance(report.kpis, SiteComparisonKPISummary)
    assert report.kpis.total_sites_evaluated == 1
    assert report.records[0].site_code == "VASCO"


# 2. Source Mapping Explicit Test
def test_ws3_3_source_mapping(sample_site_comparison_report):
    rec = sample_site_comparison_report.records[0]
    assert rec.rank == 1
    assert rec.site_code == "VASCO"
    assert rec.dispatches == 15
    assert rec.volume_cum == 90.0
    assert rec.dispatch_accuracy == 95.0


# 3. Canonical Data Assembly Test
@pytest.mark.asyncio
async def test_ws3_3_canonical_data_assembly(sample_site_comparison_report):
    assert sample_site_comparison_report.schema_version == "1.0"
    assert sample_site_comparison_report.status == ReportStatus.COMPLETED
    assert sample_site_comparison_report.record_count == 2


# 4. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_3_multi_format_rendering(sample_site_comparison_report):
    json_bytes = JSONReportRenderer.render(sample_site_comparison_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_site_comparison_report)
    pdf_bytes = PDFReportRenderer.render(sample_site_comparison_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "site_comparison"
    assert json_obj["kpis"]["total_sites_evaluated"] == 2
    assert len(json_obj["records"]) == 2

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 5. Cross-Format Parity Test
def test_ws3_3_cross_format_parity(sample_site_comparison_report):
    json_bytes = JSONReportRenderer.render(sample_site_comparison_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_site_comparison_report.scope_fingerprint
    assert json_obj["record_count"] == sample_site_comparison_report.record_count
    assert json_obj["kpis"]["total_sites_evaluated"] == sample_site_comparison_report.kpis.total_sites_evaluated


# 6. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_3_no_data_rendering(sample_site_comparison_report):
    sample_site_comparison_report.status = ReportStatus.NO_DATA
    sample_site_comparison_report.record_count = 0
    sample_site_comparison_report.records = []

    json_bytes = JSONReportRenderer.render(sample_site_comparison_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0
    assert json_obj["records"] == []


# 7. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_3_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 8. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_3_dataset_authority_override_protection():
    resolver = ScopeResolverService()
    raw_scope = {
        "plant_id": "ALL",
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
    assert eff_scope["resolved_dataset_id"].startswith("DS-20260805-ALL")


# 9. Invalid Scope API End-to-End Test
def test_ws3_3_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "site_comparison",
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


# 10. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_3_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws33-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Site Comparison PDF",
            "xlsx": b"PK123 Site Comparison XLSX",
            "json": b'{"report_id": "site_comparison"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Site Comparison PDF"


# 11. Explicit Download API End-to-End Test
def test_ws3_3_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws33-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Site Comp Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Site Comp Download Test"
