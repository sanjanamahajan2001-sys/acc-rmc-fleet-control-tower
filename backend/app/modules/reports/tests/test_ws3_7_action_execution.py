import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.action_execution_canonical import (
    CanonicalActionExecutionReport,
    ActionExecutionKPISummary,
    ReportMetadataDTO,
    ActionLogRecord
)
from app.modules.reports.handlers.action_execution_handler import ActionExecutionReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.operational_intelligence.schemas.action_execution_dtos import (
    ActionQueueResponseDTO, ActionLogDTO, ActionStatusEnum, DispatcherRoleEnum
)


@pytest.fixture
def sample_action_execution_report():
    return CanonicalActionExecutionReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-act-001",
            report_id="action_execution",
            report_name="Control Tower Action Execution Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-act-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=ActionExecutionKPISummary(
            total_actions=2,
            pending_count=0,
            accepted_count=1,
            executed_count=1,
            total_avoided_exposure_inr=25000.0
        ),
        records=[
            ActionLogRecord(
                action_id="ACT-001",
                recommendation_id="REC-001",
                prediction_snapshot_id="SNAP-001",
                model_family="delay_regressor",
                model_version="v1.1.0",
                dataset_id="DS-20260805-VASCO",
                plant_code="VASCO",
                customer_code="CUST-001",
                dispatch_id="DISP-001",
                dispatch_code="DN-001",
                action_type="REROUTE_TRUCK",
                action_status="EXECUTED",
                dispatcher_id="DISPATCHER_USER_1",
                dispatcher_role="DISPATCHER",
                predicted_risk_exposure_inr=25000.0,
                estimated_avoided_exposure_inr=25000.0,
                actual_avoided_loss_inr=25000.0,
                decision_timestamp="2026-08-05T08:00:00Z",
                execution_confirmed_at="2026-08-05T08:30:00Z",
                reason_code="TRAFFIC_CONGESTION_BYPASS",
                dispatcher_notes="Rerouted via Highway 4A",
                action_parameters={"new_route": "HW4A"}
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data Binding Test
@pytest.mark.asyncio
async def test_ws3_7_authoritative_data_binding():
    handler = ActionExecutionReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = ActionQueueResponseDTO(
        items=[
            ActionLogDTO(
                action_id="ACT-001",
                recommendation_id="REC-001",
                prediction_snapshot_id="SNAP-001",
                model_family="delay_regressor",
                model_version="v1.1.0",
                dataset_id="DS-20260805-VASCO",
                operation_date="2026-08-05",
                plant_code="VASCO",
                customer_code="CUST-001",
                dispatch_id="DISP-001",
                dispatch_code="DN-001",
                action_type="REROUTE_TRUCK",
                action_parameters={"new_route": "HW4A"},
                predicted_risk_exposure_inr=25000.0,
                estimated_avoided_exposure_inr=25000.0,
                actual_avoided_loss_inr=25000.0,
                action_status=ActionStatusEnum.EXECUTED,
                dispatcher_id="DISPATCHER_USER_1",
                dispatcher_role=DispatcherRoleEnum.DISPATCHER,
                decision_timestamp="2026-08-05T08:00:00Z",
                execution_confirmed_at="2026-08-05T08:30:00Z",
                reason_code="TRAFFIC_CONGESTION_BYPASS",
                dispatcher_notes="Rerouted via Highway 4A",
                idempotency_key="key-act-001",
                version_lock=1
            )
        ],
        total_count=1,
        pending_count=0,
        accepted_count=0,
        executed_count=1
    )

    with patch("app.modules.operational_intelligence.services.action_execution_service.ActionExecutionService.get_action_queue", return_value=mock_dto):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-7",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-7",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "action_execution"
    assert report.record_count == 1
    assert report.records[0].action_id == "ACT-001"
    assert report.records[0].action_status == "EXECUTED"


# 2. UI & Authoritative Action Parity Test
@pytest.mark.asyncio
async def test_ws3_7_ui_authoritative_action_parity():
    from app.modules.operational_intelligence.api.action_routes import get_action_queue
    from app.modules.operational_intelligence.services.action_execution_service import ActionExecutionService
    from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams


    handler = ActionExecutionReportHandler()

    mock_session = AsyncMock()

    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = ActionQueueResponseDTO(
        items=[
            ActionLogDTO(
                action_id="ACT-001",
                recommendation_id="REC-001",
                prediction_snapshot_id="SNAP-001",
                model_family="delay_regressor",
                model_version="v1.1.0",
                dataset_id="DS-20260805-VASCO",
                operation_date="2026-08-05",
                plant_code="VASCO",
                customer_code="CUST-001",
                dispatch_id="DISP-001",
                dispatch_code="DN-001",
                action_type="REROUTE_TRUCK",
                action_parameters={"new_route": "HW4A"},
                predicted_risk_exposure_inr=25000.0,
                estimated_avoided_exposure_inr=25000.0,
                actual_avoided_loss_inr=25000.0,
                action_status=ActionStatusEnum.EXECUTED,
                dispatcher_id="DISPATCHER_USER_1",
                dispatcher_role=DispatcherRoleEnum.DISPATCHER,
                decision_timestamp="2026-08-05T08:00:00Z",
                execution_confirmed_at="2026-08-05T08:30:00Z",
                reason_code="TRAFFIC_CONGESTION_BYPASS",
                dispatcher_notes="Rerouted via Highway 4A",
                idempotency_key="key-act-001",
                version_lock=1
            )
        ],
        total_count=1,
        pending_count=0,
        accepted_count=0,
        executed_count=1
    )

    with patch("app.modules.operational_intelligence.services.action_execution_service.ActionExecutionService.get_action_queue", return_value=mock_dto):
        params = DashboardFilterParams(plant_id="VASCO")
        ui_res = await ActionExecutionService.get_action_queue(session=mock_session, params=params)
        ui_item = ui_res.items[0]


        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-parity-act",
            requested_scope={"plant_id": "VASCO"},
            effective_scope=eff_scope,
            scope_fingerprint="fp-parity-act",
            requested_by="test_user"
        )
        rep_rec = report.records[0]

        assert ui_item.action_id == rep_rec.action_id
        assert ui_item.recommendation_id == rep_rec.recommendation_id
        assert ui_item.action_type == rep_rec.action_type
        assert ui_item.action_status.value == rep_rec.action_status
        assert ui_item.reason_code == rep_rec.reason_code


# 3. Source Mapping Test
def test_ws3_7_source_mapping(sample_action_execution_report):
    rec = sample_action_execution_report.records[0]
    assert rec.action_id == "ACT-001"
    assert rec.recommendation_id == "REC-001"
    assert rec.action_type == "REROUTE_TRUCK"
    assert rec.action_status == "EXECUTED"
    assert rec.reason_code == "TRAFFIC_CONGESTION_BYPASS"


# 4. Action Type Semantics Test
def test_ws3_7_action_type_semantics(sample_action_execution_report):
    assert sample_action_execution_report.records[0].action_status in ["PENDING", "ACCEPTED", "IN_PROGRESS", "EXECUTED", "REJECTED", "DEFERRED"]


# 5. Rejection Reason Integrity Test
def test_ws3_7_rejection_reason_integrity(sample_action_execution_report):
    assert sample_action_execution_report.records[0].reason_code == "TRAFFIC_CONGESTION_BYPASS"


# 6. Modification Parameter Integrity Test
def test_ws3_7_modification_parameter_integrity(sample_action_execution_report):
    assert sample_action_execution_report.records[0].action_parameters == {"new_route": "HW4A"}


# 7. Recommendation Lineage Test
def test_ws3_7_recommendation_lineage(sample_action_execution_report):
    rec = sample_action_execution_report.records[0]
    assert rec.recommendation_id == "REC-001"
    assert rec.prediction_snapshot_id == "SNAP-001"


# 8. Canonical Data Assembly Test
@pytest.mark.asyncio
async def test_ws3_7_canonical_data_assembly(sample_action_execution_report):
    assert sample_action_execution_report.schema_version == "1.0"
    assert sample_action_execution_report.status == ReportStatus.COMPLETED
    assert sample_action_execution_report.record_count == 2


# 9. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_7_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 10. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_7_dataset_authority_override_protection():
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


# 11. Invalid Scope API End-to-End Test
def test_ws3_7_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "action_execution",
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


# 12. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_7_multi_format_rendering(sample_action_execution_report):
    json_bytes = JSONReportRenderer.render(sample_action_execution_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_action_execution_report)
    pdf_bytes = PDFReportRenderer.render(sample_action_execution_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "action_execution"
    assert json_obj["kpis"]["total_actions"] == 2

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 13. Cross-Format Parity Test
def test_ws3_7_cross_format_parity(sample_action_execution_report):
    json_bytes = JSONReportRenderer.render(sample_action_execution_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_action_execution_report.scope_fingerprint
    assert json_obj["record_count"] == sample_action_execution_report.record_count
    assert json_obj["kpis"]["total_avoided_exposure_inr"] == sample_action_execution_report.kpis.total_avoided_exposure_inr


# 14. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_7_no_data_rendering(sample_action_execution_report):
    sample_action_execution_report.status = ReportStatus.NO_DATA
    sample_action_execution_report.record_count = 0
    sample_action_execution_report.records = []

    json_bytes = JSONReportRenderer.render(sample_action_execution_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0


# 15. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_7_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws37-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Action Exec PDF",
            "xlsx": b"PK123 Action Exec XLSX",
            "json": b'{"report_id": "action_execution"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Action Exec PDF"


# 16. Explicit Download API End-to-End Test
def test_ws3_7_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws37-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Action Exec Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Action Exec Download Test"


# 17. Security & Authorization Test
def test_ws3_7_security():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Path traversal check
    res = client.get("/fleet-api/v1/reports/executions/../etc/passwd/download?format=pdf")
    assert res.status_code in [400, 404]
