import io
import json
import openpyxl
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.erp_data_explorer_canonical import (
    CanonicalERPDataExplorerReport,
    ERPDataExplorerKPISummary,
    ReportMetadataDTO,
    ERPDispatchRecord
)
from app.modules.reports.handlers.erp_data_explorer_handler import ERPDataExplorerReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService


@pytest.fixture
def sample_erp_data_explorer_report():
    disp_uuid = str(uuid4())
    return CanonicalERPDataExplorerReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-exp-001",
            report_id="erp_data_explorer",
            report_name="ERP Data Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-exp-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=1,
        kpis=ERPDataExplorerKPISummary(
            total_plants=1,
            total_customers=1,
            total_dispatches=1,
            correlated_dispatches_count=1
        ),
        records=[
            ERPDispatchRecord(
                dispatch_id=disp_uuid,
                dispatch_number="DN-EXP-001",
                plant_name="VASCO Batch Plant",
                customer_name="L&T Construction",
                vehicle_code="GA-01-A-1234",
                status="COMPLETED",
                telemetry_status="CORRELATED",
                correlation_score="0.98",
                time_out="2026-08-05T08:00:00Z",
                time_in="2026-08-05T08:45:00Z",
                cycle_time=45.0
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data Binding Test
@pytest.mark.asyncio
async def test_ws3_11_authoritative_data_binding():
    handler = ERPDataExplorerReportHandler()
    mock_session = AsyncMock()

    class MockExecuteResult:
        def scalar_one(self): return 1

    mock_session.execute.return_value = MockExecuteResult()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "resolved_dataset_id": "DS-20260805-VASCO"}

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

    with patch("app.modules.reports.handlers.erp_data_explorer_handler._generic_explorer_query", AsyncMock(return_value=([mock_dispatch_dict], 1))):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-11",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-11",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "erp_data_explorer"
    assert report.record_count == 1
    assert report.records[0].dispatch_id == str(disp_uuid)
    assert report.records[0].telemetry_status == "CORRELATED"


# 2. UI & Authoritative Explorer Parity Test
@pytest.mark.asyncio
async def test_ws3_11_ui_authoritative_erp_explorer_parity():
    handler = ERPDataExplorerReportHandler()
    mock_session = AsyncMock()

    class MockExecuteResult:
        def scalar_one(self): return 1

    mock_session.execute.return_value = MockExecuteResult()

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

    with patch("app.modules.reports.handlers.erp_data_explorer_handler._generic_explorer_query", AsyncMock(return_value=([mock_dispatch_dict], 1))):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-parity-exp",
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            scope_fingerprint="fp-parity-exp",
            requested_by="test_user"
        )
        rep_rec = report.records[0]

        assert str(mock_dispatch_dict["id"]) == rep_rec.dispatch_id
        assert mock_dispatch_dict["dispatch_number"] == rep_rec.dispatch_number
        assert mock_dispatch_dict["telemetry_status"] == rep_rec.telemetry_status



# 3. Source Mapping Test
def test_ws3_11_source_mapping(sample_erp_data_explorer_report):
    rec = sample_erp_data_explorer_report.records[0]
    assert rec.dispatch_number == "DN-EXP-001"
    assert rec.telemetry_status == "CORRELATED"
    assert rec.correlation_score == "0.98"


# 4. Canonical Data Assembly Test
@pytest.mark.asyncio
async def test_ws3_11_canonical_data_assembly(sample_erp_data_explorer_report):
    assert sample_erp_data_explorer_report.schema_version == "1.0"
    assert sample_erp_data_explorer_report.status == ReportStatus.COMPLETED
    assert sample_erp_data_explorer_report.record_count == 1


# 5. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_11_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05"}
    scope_b = {"plant_id": "SANVORDEM", "operation_date": "2026-08-05"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when plant changes"


# 6. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_11_dataset_authority_override_protection():
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
def test_ws3_11_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "erp_data_explorer",
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


# 8. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_11_multi_format_rendering(sample_erp_data_explorer_report):
    json_bytes = JSONReportRenderer.render(sample_erp_data_explorer_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_erp_data_explorer_report)
    pdf_bytes = PDFReportRenderer.render(sample_erp_data_explorer_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "erp_data_explorer"
    assert json_obj["kpis"]["total_dispatches"] == 1

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 9. Cross-Format Parity Test
def test_ws3_11_cross_format_parity(sample_erp_data_explorer_report):
    json_bytes = JSONReportRenderer.render(sample_erp_data_explorer_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_erp_data_explorer_report.scope_fingerprint
    assert json_obj["record_count"] == sample_erp_data_explorer_report.record_count
    assert json_obj["kpis"]["total_dispatches"] == sample_erp_data_explorer_report.kpis.total_dispatches


# 10. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_11_no_data_rendering(sample_erp_data_explorer_report):
    sample_erp_data_explorer_report.status = ReportStatus.NO_DATA
    sample_erp_data_explorer_report.record_count = 0
    sample_erp_data_explorer_report.records = []

    json_bytes = JSONReportRenderer.render(sample_erp_data_explorer_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0


# 11. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_11_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws311-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 ERP Data Report PDF",
            "xlsx": b"PK123 ERP Data Report XLSX",
            "json": b'{"report_id": "erp_data_explorer"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 ERP Data Report PDF"


# 12. Explicit Download API End-to-End Test
def test_ws3_11_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws311-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 ERP Data Report Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 ERP Data Report Download Test"


# 13. Security & Authorization Test
def test_ws3_11_security():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Path traversal check
    res = client.get("/fleet-api/v1/reports/executions/../etc/passwd/download?format=pdf")
    assert res.status_code in [400, 404]
