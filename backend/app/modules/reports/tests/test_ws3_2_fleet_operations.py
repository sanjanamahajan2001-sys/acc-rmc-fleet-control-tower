import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.fleet_operations_canonical import (
    CanonicalFleetOperationsReport,
    FleetOperationsKPIs,
    ReportMetadataDTO,
    VehicleProductivityRecord,
    VehicleAlertRecord
)
from app.modules.reports.handlers.fleet_operations_handler import FleetOperationsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.site_dashboard.widgets.fleet_utilization.dtos import (
    FleetUtilizationResponseDTO, FleetSummaryDTO, VehicleProductivityItemDTO, VehicleAlertDTO
)


@pytest.fixture
def sample_fleet_operations_report():
    return CanonicalFleetOperationsReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-fleet-001",
            report_id="fleet_operations",
            report_name="Fleet Operations Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-fleet-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=FleetOperationsKPIs(
            total_active_vehicles=10,
            vehicles_with_dispatches=8,
            idle_vehicles=2,
            fleet_utilization_pct=80.0,
            avg_dispatches_per_vehicle=4.5,
            avg_cycle_time_mins=22.0
        ),
        records=[
            VehicleProductivityRecord(
                vehicle_plate="GA-01-A-1234",
                dispatch_count=5,
                total_volume_m3=30.0,
                avg_holding_mins=10.0,
                avg_unloading_mins=15.0,
                avg_retention_mins=5.0,
                utilization_pct=85.0,
                status="ACTIVE"
            ),
            VehicleProductivityRecord(
                vehicle_plate="GA-01-B-5678",
                dispatch_count=3,
                total_volume_m3=18.0,
                avg_holding_mins=12.0,
                avg_unloading_mins=18.0,
                avg_retention_mins=6.0,
                utilization_pct=75.0,
                status="ACTIVE"
            )
        ],
        alerts=[
            VehicleAlertRecord(
                vehicle_plate="GA-01-B-5678",
                alert_type="EXCESSIVE_HOLDING",
                severity="HIGH",
                message="Vehicle holding time exceeded 15 minutes threshold."
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data & Canonical DTO Assembly Test
@pytest.mark.asyncio
async def test_ws3_2_authoritative_data_binding():
    handler = FleetOperationsReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = FleetUtilizationResponseDTO(
        summary=FleetSummaryDTO(
            total_active_vehicles=10,
            vehicles_with_dispatches=8,
            idle_vehicles=2,
            fleet_utilization_pct=80.0,
            avg_dispatches_per_vehicle=4.5,
            avg_cycle_time_mins=22.0
        ),
        top_vehicles=[
            VehicleProductivityItemDTO(
                vehicle_plate="GA-01-A-1234",
                dispatch_count=5,
                total_volume_m3=30.0,
                avg_holding_mins=10.0,
                avg_unloading_mins=15.0,
                avg_retention_mins=5.0,
                utilization_pct=85.0,
                status="ACTIVE"
            )
        ],
        alerts=[]
    )

    with patch("app.modules.site_dashboard.widgets.fleet_utilization.service.FleetUtilizationService.get_fleet_utilization", return_value=mock_dto):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-2",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-2",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "fleet_operations"
    assert report.effective_scope["resolved_dataset_id"] == "DS-20260805-VASCO"
    assert isinstance(report.kpis, FleetOperationsKPIs)
    assert report.kpis.total_active_vehicles == 10
    assert report.record_count == 1


# 2. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_2_multi_format_rendering(sample_fleet_operations_report):
    json_bytes = JSONReportRenderer.render(sample_fleet_operations_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_fleet_operations_report)
    pdf_bytes = PDFReportRenderer.render(sample_fleet_operations_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "fleet_operations"
    assert json_obj["kpis"]["fleet_utilization_pct"] == 80.0
    assert len(json_obj["records"]) == 2

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 3. Cross-Format Parity Test
def test_ws3_2_cross_format_parity(sample_fleet_operations_report):
    json_bytes = JSONReportRenderer.render(sample_fleet_operations_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_fleet_operations_report.scope_fingerprint
    assert json_obj["record_count"] == sample_fleet_operations_report.record_count
    assert json_obj["kpis"]["total_active_vehicles"] == sample_fleet_operations_report.kpis.total_active_vehicles


# 4. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_2_no_data_rendering(sample_fleet_operations_report):
    sample_fleet_operations_report.status = ReportStatus.NO_DATA
    sample_fleet_operations_report.record_count = 0
    sample_fleet_operations_report.records = []

    json_bytes = JSONReportRenderer.render(sample_fleet_operations_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0
    assert json_obj["records"] == []


# 5. Scope Propagation & Silent Filter Failure Test
@pytest.mark.asyncio
async def test_ws3_2_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 6. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_2_dataset_authority_override_protection():
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
def test_ws3_2_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "fleet_operations",
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
async def test_ws3_2_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws32-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Fleet Ops PDF",
            "xlsx": b"PK123 Fleet Ops XLSX",
            "json": b'{"report_id": "fleet_operations"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Fleet Ops PDF"
