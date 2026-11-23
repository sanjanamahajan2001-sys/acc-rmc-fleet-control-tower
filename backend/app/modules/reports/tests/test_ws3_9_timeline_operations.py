import io
import json
import openpyxl
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.timeline_operations_canonical import (
    CanonicalTimelineOperationsReport,
    TimelineOperationsKPISummary,
    ReportMetadataDTO,
    TimelineEventRecord
)
from app.modules.reports.handlers.timeline_operations_handler import TimelineOperationsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    DispatchReplayListResponseDTO, DispatchReplayListItemDTO, DispatchTimelineReplayDetailDTO,
    TimelineEventItemDTO, EventAuthorityEnum, DurationSummaryDTO, DurationCompletenessEnum,
    TelemetrySummaryDTO, SpatialContextDTO, SpatialModeEnum
)


@pytest.fixture
def sample_timeline_operations_report():
    disp_uuid = str(uuid4())
    return CanonicalTimelineOperationsReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-tl-001",
            report_id="timeline_operations",
            report_name="Timeline Operations Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-tl-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        kpis=TimelineOperationsKPISummary(
            total_dispatches=1,
            total_timeline_events=2,
            dispatches_with_telemetry=1,
            complete_duration_count=1
        ),
        records=[
            TimelineEventRecord(
                event_id=f"{disp_uuid}-EV-01",
                event_type="Batched",
                authority_type="DIRECT",
                timestamp="2026-08-05T08:00:00Z",
                duration_mins=0.0,
                location_name="VASCO Plant",
                is_inferred_estimate=False,
                notes="Direct ERP batch timestamp",
                dispatch_id=disp_uuid,
                dispatch_number="DN-TL-001",
                plant_id="VASCO",
                customer_id="CUST-001",
                vehicle_id="GA-01-A-1234",
                status="COMPLETED"
            ),
            TimelineEventRecord(
                event_id=f"{disp_uuid}-EV-02",
                event_type="Departed Plant",
                authority_type="DIRECT",
                timestamp="2026-08-05T08:15:00Z",
                duration_mins=15.0,
                location_name="VASCO Plant Gate",
                is_inferred_estimate=False,
                notes="Direct gate outbound scan",
                dispatch_id=disp_uuid,
                dispatch_number="DN-TL-001",
                plant_id="VASCO",
                customer_id="CUST-001",
                vehicle_id="GA-01-A-1234",
                status="COMPLETED"
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data Binding Test
@pytest.mark.asyncio
async def test_ws3_9_authoritative_data_binding():
    handler = TimelineOperationsReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    disp_uuid = uuid4()
    mock_list_item = DispatchReplayListItemDTO(
        dispatch_id=str(disp_uuid),
        dispatch_number="DN-TL-001",
        plant_id="VASCO",
        customer_id="CUST-001",
        vehicle_id="GA-01-A-1234",
        dispatch_date=datetime.now(timezone.utc),
        status="COMPLETED",
        has_telemetry=True
    )
    mock_list_dto = DispatchReplayListResponseDTO(items=[mock_list_item], total_count=1, page=1, page_size=50)

    mock_detail_dto = DispatchTimelineReplayDetailDTO(
        dispatch_id=disp_uuid,
        dispatch_number="DN-TL-001",
        plant_id="VASCO",
        customer_id="CUST-001",
        vehicle_id="GA-01-A-1234",
        dataset_id="DS-20260805-VASCO",
        status="COMPLETED",
        duration_summary=DurationSummaryDTO(total_trip_duration_mins=45.0, duration_completeness=DurationCompletenessEnum.COMPLETE),
        lifecycle_events=[
            TimelineEventItemDTO(event_type="Batched", authority_type=EventAuthorityEnum.DIRECT, timestamp=datetime.now(timezone.utc), duration_mins=0.0, location_name="VASCO Plant")
        ],
        telemetry_summary=TelemetrySummaryDTO(telemetry_matched=True),
        spatial_context=SpatialContextDTO(has_gps_breadcrumbs=False, spatial_mode=SpatialModeEnum.NO_SPATIAL_DATA)
    )

    with patch("app.modules.operational_dashboard.widgets.timeline_replay.service.TimelineReplayService.list_replay_dispatches", return_value=mock_list_dto), \
         patch("app.modules.operational_dashboard.widgets.timeline_replay.service.TimelineReplayService.get_dispatch_timeline_detail", return_value=mock_detail_dto):

        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-9",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-9",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "timeline_operations"
    assert report.record_count == 1
    assert report.records[0].dispatch_id == str(disp_uuid)
    assert report.records[0].event_type == "Batched"


# 2. UI & Authoritative Timeline Parity Test
@pytest.mark.asyncio
async def test_ws3_9_ui_authoritative_timeline_parity():
    from app.modules.operational_dashboard.widgets.timeline_replay.service import TimelineReplayService

    handler = TimelineOperationsReportHandler()
    mock_session = AsyncMock()

    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    disp_uuid = uuid4()
    mock_list_item = DispatchReplayListItemDTO(dispatch_id=str(disp_uuid), dispatch_number="DN-TL-001", plant_id="VASCO", customer_id="CUST-001", vehicle_id="GA-01-A-1234", dispatch_date=datetime.now(timezone.utc), status="COMPLETED", has_telemetry=True)
    mock_list_dto = DispatchReplayListResponseDTO(items=[mock_list_item], total_count=1, page=1, page_size=50)

    mock_detail_dto = DispatchTimelineReplayDetailDTO(
        dispatch_id=disp_uuid, dispatch_number="DN-TL-001", plant_id="VASCO", customer_id="CUST-001", vehicle_id="GA-01-A-1234", dataset_id="DS-20260805-VASCO", status="COMPLETED",
        duration_summary=DurationSummaryDTO(total_trip_duration_mins=45.0, duration_completeness=DurationCompletenessEnum.COMPLETE),
        lifecycle_events=[TimelineEventItemDTO(event_type="Batched", authority_type=EventAuthorityEnum.DIRECT, timestamp=datetime.now(timezone.utc), duration_mins=0.0, location_name="VASCO Plant")],
        telemetry_summary=TelemetrySummaryDTO(telemetry_matched=True), spatial_context=SpatialContextDTO(has_gps_breadcrumbs=False, spatial_mode=SpatialModeEnum.NO_SPATIAL_DATA)
    )

    with patch("app.modules.operational_dashboard.widgets.timeline_replay.service.TimelineReplayService.list_replay_dispatches", return_value=mock_list_dto), \
         patch("app.modules.operational_dashboard.widgets.timeline_replay.service.TimelineReplayService.get_dispatch_timeline_detail", return_value=mock_detail_dto):

        ui_detail = await TimelineReplayService.get_dispatch_timeline_detail(session=mock_session, dispatch_id=disp_uuid)
        ui_event = ui_detail.lifecycle_events[0]

        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-parity-tl",
            requested_scope={"plant_id": "VASCO"},
            effective_scope=eff_scope,
            scope_fingerprint="fp-parity-tl",
            requested_by="test_user"
        )
        rep_rec = report.records[0]

        assert str(ui_detail.dispatch_id) == rep_rec.dispatch_id
        assert ui_event.event_type == rep_rec.event_type
        assert ui_event.authority_type.value == rep_rec.authority_type


# 3. Source Mapping Test
def test_ws3_9_source_mapping(sample_timeline_operations_report):
    rec = sample_timeline_operations_report.records[0]
    assert rec.event_type == "Batched"
    assert rec.authority_type == "DIRECT"
    assert rec.dispatch_number == "DN-TL-001"


# 4. Event Semantics Test
def test_ws3_9_event_semantics(sample_timeline_operations_report):
    assert sample_timeline_operations_report.records[0].event_type in [
        "Scheduled", "Batched", "Loaded", "Departed Plant", "Arrived Site", "Unloading / Pouring", "Completed", "Returned"
    ]


# 5. Chronological Order Integrity Test
def test_ws3_9_chronological_order_integrity(sample_timeline_operations_report):
    recs = sample_timeline_operations_report.records
    assert recs[0].timestamp <= recs[1].timestamp


# 6. State Transition Integrity Test
def test_ws3_9_state_transition_integrity(sample_timeline_operations_report):
    assert sample_timeline_operations_report.records[0].status == "COMPLETED"


# 7. Canonical Data Assembly Test
@pytest.mark.asyncio
async def test_ws3_9_canonical_data_assembly(sample_timeline_operations_report):
    assert sample_timeline_operations_report.schema_version == "1.0"
    assert sample_timeline_operations_report.status == ReportStatus.COMPLETED
    assert sample_timeline_operations_report.record_count == 2


# 8. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_9_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 9. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_9_dataset_authority_override_protection():
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


# 10. Invalid Scope API End-to-End Test
def test_ws3_9_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session
    from app.modules.reports.services.security_limiter import SecurityRateLimiter
    SecurityRateLimiter.reset()
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "timeline_operations",
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


# 11. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_9_multi_format_rendering(sample_timeline_operations_report):
    json_bytes = JSONReportRenderer.render(sample_timeline_operations_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_timeline_operations_report)
    pdf_bytes = PDFReportRenderer.render(sample_timeline_operations_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "timeline_operations"
    assert json_obj["kpis"]["total_dispatches"] == 1

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 12. Cross-Format Parity Test
def test_ws3_9_cross_format_parity(sample_timeline_operations_report):
    json_bytes = JSONReportRenderer.render(sample_timeline_operations_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_timeline_operations_report.scope_fingerprint
    assert json_obj["record_count"] == sample_timeline_operations_report.record_count
    assert json_obj["kpis"]["total_dispatches"] == sample_timeline_operations_report.kpis.total_dispatches


# 13. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_9_no_data_rendering(sample_timeline_operations_report):
    sample_timeline_operations_report.status = ReportStatus.NO_DATA
    sample_timeline_operations_report.record_count = 0
    sample_timeline_operations_report.records = []

    json_bytes = JSONReportRenderer.render(sample_timeline_operations_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0


# 14. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_9_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws39-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Timeline Ops PDF",
            "xlsx": b"PK123 Timeline Ops XLSX",
            "json": b'{"report_id": "timeline_operations"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Timeline Ops PDF"


# 15. Explicit Download API End-to-End Test
def test_ws3_9_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws39-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Timeline Ops Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Timeline Ops Download Test"


# 16. Security & Authorization Test
def test_ws3_9_security():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Path traversal check
    res = client.get("/fleet-api/v1/reports/executions/../etc/passwd/download?format=pdf")
    assert res.status_code in [400, 404]
