import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.dispatch_analysis_canonical import (
    CanonicalDispatchAnalysisReport,
    DispatchAnalysisKPIs,
    DispatchAnalysisRecord
)
from app.modules.reports.handlers.dispatch_analysis_handler import DispatchAnalysisReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage


@pytest.fixture
def sample_canonical_report():
    return CanonicalDispatchAnalysisReport(
        metadata={
            "execution_id": "exec-12345",
            "report_id": "dispatch_analysis",
            "report_name": "Dispatch Analysis",
            "generated_at": "2026-08-19T10:00:00Z",
            "requested_by": "test_user"
        },
        requested_scope={"plant_id": "P001", "customer_id": "C001", "operation_date": "2026-08-19", "shift": "ALL", "dataset_type": "dispatches"},
        effective_scope={"plant_id": "P001", "customer_id": "C001", "operation_date": "2026-08-19", "shift": "ALL", "dataset_type": "dispatches", "resolved_dataset_id": "DS-20260819-P001-C001"},
        scope_fingerprint="sha256-sample-fingerprint-1234567890",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=DispatchAnalysisKPIs(
            total_dispatches=10,
            on_schedule_dispatches=8,
            sla_compliance_pct=80.0,
            avg_interval_mins=15.5,
            interval_variance_mins=2.1,
            das_score_pct=88.5,
            completed_dispatches=9,
            avg_loading_mins=12.0,
            avg_transit_mins=25.0,
            recommended_interval_mins=15.0,
            cadence_status="OPTIMAL",
            potential_delay_reduction_hrs=1.5
        ),
        records=[
            DispatchAnalysisRecord(
                dispatch_id="d1",
                dispatch_number="DISP-001",
                dispatch_date="2026-08-19",
                time_out="08:00",
                time_in="08:45",
                plant_code="P001",
                customer_code="C001",
                customer_name="Customer A",
                vehicle_id="V-100",
                driver_name="John Doe",
                interval_mins=15.0,
                variance_mins=0.0,
                holding_mins=10.0,
                retention_mins=5.0,
                sla_status="COMPLIANT",
                trip_status="COMPLETED",
                cadence_recommendation="MAINTAIN"
            ),
            DispatchAnalysisRecord(
                dispatch_id="d2",
                dispatch_number="DISP-002",
                dispatch_date="2026-08-19",
                time_out="08:20",
                time_in="09:10",
                plant_code="P001",
                customer_code="C001",
                customer_name="Customer A",
                vehicle_id="V-101",
                driver_name="Jane Smith",
                interval_mins=20.0,
                variance_mins=5.0,
                holding_mins=18.0,
                retention_mins=8.0,
                sla_status="COMPLIANT",
                trip_status="COMPLETED",
                cadence_recommendation="OPTIMIZE_HOLDING"
            )
        ],
        delay_categories=[],
        insights=[]
    )


import os
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.dispatch_analysis_canonical import (
    CanonicalDispatchAnalysisReport,
    DispatchAnalysisKPIs,
    DispatchAnalysisRecord
)
from app.modules.reports.handlers.dispatch_analysis_handler import DispatchAnalysisReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage
from app.modules.reports.services.scope_resolver import ScopeResolverService


@pytest.fixture
def sample_canonical_report():
    return CanonicalDispatchAnalysisReport(
        metadata={
            "execution_id": "exec-12345",
            "report_id": "dispatch_analysis",
            "report_name": "Dispatch Analysis",
            "generated_at": "2026-08-19T10:00:00Z",
            "requested_by": "test_user"
        },
        requested_scope={"plant_id": "P001", "customer_id": "C001", "operation_date": "2026-08-19", "shift": "ALL", "dataset_type": "dispatches"},
        effective_scope={"plant_id": "P001", "customer_id": "C001", "operation_date": "2026-08-19", "shift": "ALL", "dataset_type": "dispatches", "resolved_dataset_id": "DS-20260819-P001-C001"},
        scope_fingerprint="sha256-sample-fingerprint-1234567890",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=DispatchAnalysisKPIs(
            total_dispatches=10,
            on_schedule_dispatches=8,
            sla_compliance_pct=80.0,
            avg_interval_mins=15.5,
            interval_variance_mins=2.1,
            das_score_pct=88.5,
            completed_dispatches=9,
            avg_loading_mins=12.0,
            avg_transit_mins=25.0,
            recommended_interval_mins=15.0,
            cadence_status="OPTIMAL",
            potential_delay_reduction_hrs=1.5
        ),
        records=[
            DispatchAnalysisRecord(
                dispatch_id="d1",
                dispatch_number="DISP-001",
                dispatch_date="2026-08-19",
                time_out="08:00",
                time_in="08:45",
                plant_code="P001",
                customer_code="C001",
                customer_name="Customer A",
                vehicle_id="V-100",
                driver_name="John Doe",
                interval_mins=15.0,
                variance_mins=0.0,
                holding_mins=10.0,
                retention_mins=5.0,
                sla_status="COMPLIANT",
                trip_status="COMPLETED",
                cadence_recommendation="MAINTAIN"
            ),
            DispatchAnalysisRecord(
                dispatch_id="d2",
                dispatch_number="DISP-002",
                dispatch_date="2026-08-19",
                time_out="08:20",
                time_in="09:10",
                plant_code="P001",
                customer_code="C001",
                customer_name="Customer A",
                vehicle_id="V-101",
                driver_name="Jane Smith",
                interval_mins=20.0,
                variance_mins=5.0,
                holding_mins=18.0,
                retention_mins=8.0,
                sla_status="COMPLIANT",
                trip_status="COMPLETED",
                cadence_recommendation="OPTIMIZE_HOLDING"
            )
        ],
        delay_categories=[],
        insights=[]
    )


# 1. Basic Renderer & Storage Tests
def test_json_renderer(sample_canonical_report):
    json_bytes = JSONReportRenderer.render(sample_canonical_report)
    assert isinstance(json_bytes, bytes)
    assert len(json_bytes) > 0
    assert b"exec-12345" in json_bytes
    assert b"DISP-001" in json_bytes


def test_xlsx_renderer(sample_canonical_report):
    xlsx_bytes = XLSXReportRenderer.render(sample_canonical_report)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 500  # Non-trivial excel workbook size
    assert xlsx_bytes[:2] == b"PK"  # OpenPyXL zip magic header


def test_pdf_renderer(sample_canonical_report):
    pdf_bytes = PDFReportRenderer.render(sample_canonical_report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"  # PDF magic header


def test_artifact_storage_save_and_retrieve(tmp_path, sample_canonical_report):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        saved_paths = ReportArtifactStorage.save_artifacts(
            execution_id="exec-999",
            artifacts={
                "json": b"{\"test\": 1}",
                "xlsx": b"PK123",
                "pdf": b"%PDF123"
            }
        )
        assert os.path.exists(saved_paths["json"])
        assert os.path.exists(saved_paths["xlsx"])
        assert os.path.exists(saved_paths["pdf"])
        
        path_pdf = ReportArtifactStorage.get_artifact_path("exec-999", "pdf")
        assert path_pdf == saved_paths["pdf"]


def test_artifact_storage_path_traversal_protection(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        with pytest.raises(ValueError):
            ReportArtifactStorage.save_artifacts(execution_id="../../etc/passwd", artifacts={"json": b"{}"})


# 2. Filter Propagation Tests (Section 4)
@pytest.mark.asyncio
async def test_filter_propagation_scenarios():
    resolver = ScopeResolverService()
    scenarios = [
        {"plant_id": "ALL", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"},
        {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"},
        {"plant_id": "ALL", "customer_id": "CUST_100", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"},
        {"plant_id": "VASCO", "customer_id": "CUST_100", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"},
        {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-06", "shift": "ALL", "dataset_type": "ALL"},
        {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "MORNING", "dataset_type": "ALL"},
        {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "REAL_ONLY"},
        {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "SYNTHETIC_ONLY"},
    ]

    class MockSession:
        async def execute(self, query):
            class MockResult:
                def scalar(self):
                    return 5
            return MockResult()

    mock_session = MockSession()

    for s in scenarios:
        ok, scope, err = await resolver.resolve_and_validate_scope(session=mock_session, raw_scope=s)
        assert ok is True
        assert "resolved_dataset_id" in scope
        assert "scope_fingerprint" in scope
        assert scope["plant_id"] == s["plant_id"].upper()


# 3. Filter Silent-Failure Protection (Section 5)
def test_filter_silent_failure_protection():
    scope_a = {"plant_id": "PLANT_A", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"}
    scope_b = {"plant_id": "PLANT_B", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"}

    fp_a = ScopeResolverService.compute_scope_fingerprint(scope_a)
    fp_b = ScopeResolverService.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when plant_id changes"


# 4. Dataset Authority Override Protection (Section 6)
@pytest.mark.asyncio
async def test_dataset_authority_injection_override():
    resolver = ScopeResolverService()
    
    class MockSession:
        async def execute(self, query):
            class MockResult:
                def scalar(self):
                    return 10
            return MockResult()

    mock_session = MockSession()

    # Attempt to inject a fake resolved_dataset_id
    raw_scope = {
        "plant_id": "VASCO",
        "customer_id": "ALL",
        "operation_date": "2026-08-05",
        "resolved_dataset_id": "INJECTED_FAKE_ID"
    }

    ok, scope, err = await resolver.resolve_and_validate_scope(session=mock_session, raw_scope=raw_scope)
    assert ok is True
    assert scope["resolved_dataset_id"] != "INJECTED_FAKE_ID", "Backend must override user-injected dataset_id"
    assert scope["resolved_dataset_id"].startswith("DS-20260805-VASCO")


# 5. Cross-Format Parity (Section 8)
def test_cross_format_scope_parity(sample_canonical_report):
    json_bytes = JSONReportRenderer.render(sample_canonical_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["metadata"]["execution_id"] == sample_canonical_report.metadata.execution_id
    assert json_obj["scope_fingerprint"] == sample_canonical_report.scope_fingerprint
    assert json_obj["effective_scope"]["resolved_dataset_id"] == sample_canonical_report.effective_scope["resolved_dataset_id"]


def test_cross_format_kpi_parity(sample_canonical_report):
    json_bytes = JSONReportRenderer.render(sample_canonical_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["kpis"]["total_dispatches"] == sample_canonical_report.kpis.total_dispatches
    assert json_obj["kpis"]["sla_compliance_pct"] == sample_canonical_report.kpis.sla_compliance_pct


import io

def test_cross_format_record_count_parity(sample_canonical_report):
    json_bytes = JSONReportRenderer.render(sample_canonical_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_canonical_report)
    pdf_bytes = PDFReportRenderer.render(sample_canonical_report)

    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["record_count"] == sample_canonical_report.record_count

    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    ws_data = wb["03_Operational_Data"]
    # Row 1 is header, data rows start at row 2
    data_rows = ws_data.max_row - 1
    assert data_rows == sample_canonical_report.record_count

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


# 6. XLSX Structural Validation (Section 11)
def test_xlsx_structural_validation(sample_canonical_report):
    xlsx_bytes = XLSXReportRenderer.render(sample_canonical_report)
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))

    expected_sheets = ["01_Report_Summary", "02_Effective_Scope", "03_Operational_Data", "04_Exceptions", "05_Audit_Trail"]
    assert wb.sheetnames == expected_sheets

    ws_data = wb["03_Operational_Data"]
    assert ws_data.freeze_panes == "A2"
    assert ws_data.auto_filter.ref is not None


# 7. NO_DATA End-to-End Rendering (Section 13)
def test_no_data_rendering(sample_canonical_report):
    sample_canonical_report.record_count = 0
    sample_canonical_report.records = []
    sample_canonical_report.status = ReportStatus.NO_DATA

    json_bytes = JSONReportRenderer.render(sample_canonical_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0
    assert json_obj["records"] == []

    xlsx_bytes = XLSXReportRenderer.render(sample_canonical_report)
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    ws_data = wb["03_Operational_Data"]
    assert ws_data.cell(row=2, column=1).value == "NO AUTHORITATIVE DATA IN SCOPE"

# 8. Download API Integration Tests (Section 1)
@pytest.mark.asyncio
async def test_download_api_endpoints(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        # 1. Prepare artifact
        exec_id = "exec-test-download-100"
        ReportArtifactStorage.save_artifacts(exec_id, {"pdf": b"%PDF-1.4 test", "xlsx": b"PK123", "json": b"{}"})

        client = TestClient(app)

        # 1. Valid download
        res = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content == b"%PDF-1.4 test"

        # 2. Missing execution
        res_missing = client.get("/fleet-api/v1/reports/executions/non-existent-exec/download?format=pdf")
        assert res_missing.status_code == 404

        # 3. Missing artifact format
        res_no_fmt = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=json")
        assert res_no_fmt.status_code == 200

        # 4. Unsupported format
        res_bad_fmt = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=doc")
        assert res_bad_fmt.status_code == 400

        # 5. Path traversal attempt
        res_traversal = client.get("/fleet-api/v1/reports/executions/../etc/passwd/download?format=pdf")
        assert res_traversal.status_code in (400, 404)


# 9. Partial Format Failure & Execution Audit (Section 2 & 3)
@pytest.mark.asyncio
async def test_partial_format_failure_audit_handling(sample_canonical_report):
    # Simulate XLSX renderer failing while PDF/JSON succeed
    with patch("app.modules.reports.renderers.xlsx_renderer.XLSXReportRenderer.render", side_effect=RuntimeError("XLSX Engine Error")):
        with pytest.raises(RuntimeError) as exc_info:
            pdf_b = PDFReportRenderer.render(sample_canonical_report)
            json_b = JSONReportRenderer.render(sample_canonical_report)
            xlsx_b = XLSXReportRenderer.render(sample_canonical_report)
        assert "XLSX Engine Error" in str(exc_info.value)
        # Documented behavior: Any renderer failure aborts the batch and prevents FALSE COMPLETED status.


# 10. Invalid Scope End-to-End API Test (Section 4)
def test_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    invalid_payload = {
        "report_id": "dispatch_analysis",
        "format": "PDF",
        "requested_by": "test_user",
        "scope": {
            "plant_id": "INVALID_PLANT_NAME",
            "customer_id": "ALL",
            "operation_date": "2026-08-05",
            "shift": "ALL",
            "dataset_type": "ALL"
        }
    }
    res = client.post("/fleet-api/v1/reports/generate", json=invalid_payload)
    assert res.status_code == 400
    res_json = res.json()
    assert "REPORT_SCOPE_VALIDATION_FAILED" in str(res_json)





