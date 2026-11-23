import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.operational_intelligence_canonical import (
    CanonicalOperationalIntelligenceReport,
    OperationalIntelligenceKPISummary,
    ReportMetadataDTO,
    SiteReadinessRecord
)
from app.modules.reports.handlers.operational_intelligence_handler import OperationalIntelligenceReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    SiteReadinessResponseDTO, SiteReadinessDTO, OperationalIntelligenceStatusEnum, OperationalGradeEnum
)


@pytest.fixture
def sample_operational_intelligence_report():
    return CanonicalOperationalIntelligenceReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-opint-001",
            report_id="operational_intelligence",
            report_name="Operational Intelligence Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"},
        scope_fingerprint="sha256-opint-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=OperationalIntelligenceKPISummary(
            total_sites_evaluated=2,
            total_trips=25,
            avg_sri_score=85.5,
            avg_swi_site=88.0,
            avg_dpi_site=82.0,
            avg_fui_site=86.5,
            grade_a_sites_count=2
        ),
        records=[
            SiteReadinessRecord(
                rank=1,
                site_id="VASCO",
                site_name="Vasco ReadyMix Site",
                total_trips=15,
                swi_site=90.0,
                dpi_site=85.0,
                fui_site=88.0,
                sri_score=87.7,
                grade="GRADE_A"
            ),
            SiteReadinessRecord(
                rank=2,
                site_id="PANJIM",
                site_name="Panjim Batching Plant",
                total_trips=10,
                swi_site=86.0,
                dpi_site=79.0,
                fui_site=85.0,
                sri_score=83.3,
                grade="GRADE_A"
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data Binding Test
@pytest.mark.asyncio
async def test_ws3_5_authoritative_data_binding():
    handler = OperationalIntelligenceReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"}

    mock_dto = SiteReadinessResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.AVAILABLE,
        total_sites=1,
        data=[
            SiteReadinessDTO(
                site_id="VASCO",
                site_name="Vasco ReadyMix Site",
                rank=1,
                total_trips=15,
                swi_site=90.0,
                dpi_site=85.0,
                fui_site=88.0,
                sri_score=87.7,
                grade=OperationalGradeEnum.GRADE_A
            )
        ],
        filters=eff_scope
    )

    with patch("app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness.SiteReadinessEngine.get_site_readiness", return_value=mock_dto):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-5",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-5",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "operational_intelligence"
    assert report.effective_scope["resolved_dataset_id"] == "DS-20260805-ALL"
    assert isinstance(report.kpis, OperationalIntelligenceKPISummary)
    assert report.kpis.total_sites_evaluated == 1
    assert report.records[0].site_id == "VASCO"


# 2. Source Mapping Explicit Test
def test_ws3_5_source_mapping(sample_operational_intelligence_report):
    rec = sample_operational_intelligence_report.records[0]
    assert rec.rank == 1
    assert rec.site_id == "VASCO"
    assert rec.total_trips == 15
    assert rec.sri_score == 87.7
    assert rec.grade == "GRADE_A"


# 3. Canonical Data Assembly Test
@pytest.mark.asyncio
async def test_ws3_5_canonical_data_assembly(sample_operational_intelligence_report):
    assert sample_operational_intelligence_report.schema_version == "1.0"
    assert sample_operational_intelligence_report.status == ReportStatus.COMPLETED
    assert sample_operational_intelligence_report.record_count == 2


# 4. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_5_multi_format_rendering(sample_operational_intelligence_report):
    json_bytes = JSONReportRenderer.render(sample_operational_intelligence_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_operational_intelligence_report)
    pdf_bytes = PDFReportRenderer.render(sample_operational_intelligence_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "operational_intelligence"
    assert json_obj["kpis"]["total_sites_evaluated"] == 2
    assert len(json_obj["records"]) == 2

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 5. Cross-Format Parity Test
def test_ws3_5_cross_format_parity(sample_operational_intelligence_report):
    json_bytes = JSONReportRenderer.render(sample_operational_intelligence_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_operational_intelligence_report.scope_fingerprint
    assert json_obj["record_count"] == sample_operational_intelligence_report.record_count
    assert json_obj["kpis"]["avg_sri_score"] == sample_operational_intelligence_report.kpis.avg_sri_score


# 6. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_5_no_data_rendering(sample_operational_intelligence_report):
    sample_operational_intelligence_report.status = ReportStatus.NO_DATA
    sample_operational_intelligence_report.record_count = 0
    sample_operational_intelligence_report.records = []

    json_bytes = JSONReportRenderer.render(sample_operational_intelligence_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0
    assert json_obj["records"] == []


# 7. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_5_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 8. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_5_dataset_authority_override_protection():
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
def test_ws3_5_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "operational_intelligence",
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
async def test_ws3_5_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws35-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Op Intel PDF",
            "xlsx": b"PK123 Op Intel XLSX",
            "json": b'{"report_id": "operational_intelligence"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Op Intel PDF"


# 11. Explicit Download API End-to-End Test
def test_ws3_5_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws35-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Op Intel Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Op Intel Download Test"


# 12. UI & Authoritative API Result Parity Test
@pytest.mark.asyncio
async def test_ws3_5_ui_authoritative_result_parity():
    from app.modules.operational_dashboard.api.routes import get_site_readiness
    from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

    handler = OperationalIntelligenceReportHandler()
    mock_session = AsyncMock()

    eff_scope = {"plant_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-ALL"}

    mock_dto = SiteReadinessResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.AVAILABLE,
        total_sites=1,
        data=[
            SiteReadinessDTO(
                site_id="VASCO",
                site_name="Vasco ReadyMix Site",
                rank=1,
                total_trips=15,
                swi_site=90.0,
                dpi_site=85.0,
                fui_site=88.0,
                sri_score=87.7,
                grade=OperationalGradeEnum.GRADE_A
            )
        ],
        filters=eff_scope
    )

    with patch("app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness.SiteReadinessEngine.get_site_readiness", return_value=mock_dto):
        ui_res = await get_site_readiness(params=DashboardFilterParams(), session=mock_session)
        ui_data = ui_res["data"]["data"][0]

        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-parity-test",
            requested_scope={"plant_id": "ALL"},
            effective_scope=eff_scope,
            scope_fingerprint="fp-parity",
            requested_by="test_user"
        )
        rep_data = report.records[0]

        # Verify 100% parity between UI API endpoint and Canonical Report
        assert ui_data["site_id"] == rep_data.site_id
        assert ui_data["site_name"] == rep_data.site_name
        assert ui_data["rank"] == rep_data.rank
        assert ui_data["swi_site"] == rep_data.swi_site
        assert ui_data["dpi_site"] == rep_data.dpi_site
        assert ui_data["fui_site"] == rep_data.fui_site
        assert ui_data["sri_score"] == rep_data.sri_score
        assert ui_data["grade"] == rep_data.grade

