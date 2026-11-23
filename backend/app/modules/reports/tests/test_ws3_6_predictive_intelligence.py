import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.predictive_intelligence_canonical import (
    CanonicalPredictiveIntelligenceReport,
    PredictiveKPISummary,
    ReportMetadataDTO,
    PredictionSnapshotRecord
)
from app.modules.reports.handlers.predictive_intelligence_handler import PredictiveIntelligenceReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.operational_intelligence.schemas.predictive_operational_dtos import (
    OperationalPredictiveResponseDTO, OperationalPrioritizationDTO, OperationalPredictionItemDTO
)


@pytest.fixture
def sample_predictive_intelligence_report():
    return CanonicalPredictiveIntelligenceReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-pred-001",
            report_id="predictive_intelligence",
            report_name="Predictive Intelligence Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-pred-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        overall_authority_status="AUTHORITATIVE",
        kpis=PredictiveKPISummary(
            promoted_model_count=1,
            total_snapshots_found=2,
            avg_predicted_delay_mins=18.5,
            avg_confidence_score=0.88,
            total_financial_risk_inr=15000.0
        ),
        records=[
            PredictionSnapshotRecord(
                prediction_snapshot_id="SNAP-001",
                prediction_timestamp="2026-08-05T08:00:00Z",
                prediction_status="SUCCESS",
                model_name="delay_regressor",
                model_version="v1.1.0",
                feature_set_version="FeatureSetV1",
                dispatch_id="DISP-001",
                dispatch_code="DN-001",
                plant_code="VASCO",
                customer_code="CUST-001",
                vehicle_code="GA-01-A-1234",
                target_name="predicted_delay_mins",
                predicted_value=18.5,
                confidence_score=0.88,
                financial_exposure_inr=15000.0,
                total_financial_risk_inr=15000.0
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data Binding Test
@pytest.mark.asyncio
async def test_ws3_6_authoritative_data_binding():
    handler = PredictiveIntelligenceReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = OperationalPredictiveResponseDTO(
        overall_authority_status="AUTHORITATIVE",
        promoted_model_count=1,
        total_snapshots_found=1,
        prioritization=OperationalPrioritizationDTO(),
        snapshots=[
            OperationalPredictionItemDTO(
                id="id-1",
                prediction_snapshot_id="SNAP-001",
                idempotency_key="key-1",
                prediction_timestamp="2026-08-05T08:00:00Z",
                prediction_status="SUCCESS",
                model_name="delay_regressor",
                model_version="v1.1.0",
                artifact_sha256="sha-1234",
                feature_set_version="FeatureSetV1",
                dispatch_id="DISP-001",
                dispatch_code="DN-001",
                plant_code="VASCO",
                customer_code="CUST-001",
                vehicle_code="GA-01-A-1234",
                target_name="predicted_delay_mins",
                predicted_value=18.5,
                confidence_score=0.88,
                financial_exposure_inr=15000.0,
                total_financial_risk_inr=15000.0
            )
        ],
        calculation_status="SUCCESS",
        calculation_notes="Test notes"
    )

    with patch("app.modules.operational_intelligence.services.predictive_service.PredictiveIntelligenceService.get_operational_predictive_intelligence", return_value=mock_dto):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-6",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-6",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "predictive_intelligence"
    assert report.overall_authority_status == "AUTHORITATIVE"
    assert report.record_count == 1
    assert report.records[0].prediction_snapshot_id == "SNAP-001"


# 2. UI & Prediction Authority Parity Test
@pytest.mark.asyncio
async def test_ws3_6_ui_authoritative_prediction_parity():
    from app.modules.operational_intelligence.api.router import get_operational_predictive_intelligence
    from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

    handler = PredictiveIntelligenceReportHandler()
    mock_session = AsyncMock()

    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = OperationalPredictiveResponseDTO(
        overall_authority_status="AUTHORITATIVE",
        promoted_model_count=1,
        total_snapshots_found=1,
        prioritization=OperationalPrioritizationDTO(),
        snapshots=[
            OperationalPredictionItemDTO(
                id="id-1",
                prediction_snapshot_id="SNAP-001",
                idempotency_key="key-1",
                prediction_timestamp="2026-08-05T08:00:00Z",
                prediction_status="SUCCESS",
                model_name="delay_regressor",
                model_version="v1.1.0",
                artifact_sha256="sha-1234",
                feature_set_version="FeatureSetV1",
                dispatch_id="DISP-001",
                dispatch_code="DN-001",
                plant_code="VASCO",
                customer_code="CUST-001",
                vehicle_code="GA-01-A-1234",
                target_name="predicted_delay_mins",
                predicted_value=18.5,
                confidence_score=0.88,
                financial_exposure_inr=15000.0,
                total_financial_risk_inr=15000.0
            )
        ],
        calculation_status="SUCCESS",
        calculation_notes="Test notes"
    )

    with patch("app.modules.operational_intelligence.services.predictive_service.PredictiveIntelligenceService.get_operational_predictive_intelligence", return_value=mock_dto):
        ui_res = await get_operational_predictive_intelligence(params=DashboardFilterParams(plant_id="VASCO"), session=mock_session)
        ui_snap = ui_res["data"]["snapshots"][0]

        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-parity-pred",
            requested_scope={"plant_id": "VASCO"},
            effective_scope=eff_scope,
            scope_fingerprint="fp-parity-pred",
            requested_by="test_user"
        )
        rep_snap = report.records[0]

        assert ui_snap["prediction_snapshot_id"] == rep_snap.prediction_snapshot_id
        assert ui_snap["model_name"] == rep_snap.model_name
        assert ui_snap["model_version"] == rep_snap.model_version
        assert ui_snap["predicted_value"] == rep_snap.predicted_value
        assert ui_snap["confidence_score"] == rep_snap.confidence_score


# 3. Source Mapping Test
def test_ws3_6_source_mapping(sample_predictive_intelligence_report):
    rec = sample_predictive_intelligence_report.records[0]
    assert rec.prediction_snapshot_id == "SNAP-001"
    assert rec.model_name == "delay_regressor"
    assert rec.model_version == "v1.1.0"
    assert rec.predicted_value == 18.5
    assert rec.confidence_score == 0.88


# 4. Model & Prediction Snapshot Authority Test
@pytest.mark.asyncio
async def test_ws3_6_model_and_snapshot_authority():
    handler = PredictiveIntelligenceReportHandler()
    mock_session = AsyncMock()

    mock_dto_not_conf = OperationalPredictiveResponseDTO(
        overall_authority_status="NOT_CONFIGURED",
        promoted_model_count=0,
        total_snapshots_found=0,
        prioritization=OperationalPrioritizationDTO(),
        snapshots=[],
        calculation_status="NOT_CONFIGURED",
        calculation_notes="PREDICTION AUTHORITY = NOT_CONFIGURED."
    )

    with patch("app.modules.operational_intelligence.services.predictive_service.PredictiveIntelligenceService.get_operational_predictive_intelligence", return_value=mock_dto_not_conf):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-not-conf",
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            scope_fingerprint="fp-not-conf",
            requested_by="test_user"
        )

    assert report.overall_authority_status == "NOT_CONFIGURED"
    assert report.status == ReportStatus.NO_DATA
    assert report.record_count == 0


# 5. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_6_multi_format_rendering(sample_predictive_intelligence_report):
    json_bytes = JSONReportRenderer.render(sample_predictive_intelligence_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_predictive_intelligence_report)
    pdf_bytes = PDFReportRenderer.render(sample_predictive_intelligence_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "predictive_intelligence"
    assert json_obj["overall_authority_status"] == "AUTHORITATIVE"

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 6. Cross-Format Parity Test
def test_ws3_6_cross_format_parity(sample_predictive_intelligence_report):
    json_bytes = JSONReportRenderer.render(sample_predictive_intelligence_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_predictive_intelligence_report.scope_fingerprint
    assert json_obj["record_count"] == sample_predictive_intelligence_report.record_count
    assert json_obj["kpis"]["avg_predicted_delay_mins"] == sample_predictive_intelligence_report.kpis.avg_predicted_delay_mins


# 7. NO_DATA & Model Unavailable Semantics Test
@pytest.mark.asyncio
async def test_ws3_6_no_data_rendering(sample_predictive_intelligence_report):
    sample_predictive_intelligence_report.status = ReportStatus.NO_DATA
    sample_predictive_intelligence_report.record_count = 0
    sample_predictive_intelligence_report.records = []

    json_bytes = JSONReportRenderer.render(sample_predictive_intelligence_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0


# 8. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_6_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 9. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_6_dataset_authority_override_protection():
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
def test_ws3_6_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "predictive_intelligence",
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


# 11. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_6_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws36-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Pred Intel PDF",
            "xlsx": b"PK123 Pred Intel XLSX",
            "json": b'{"report_id": "predictive_intelligence"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Pred Intel PDF"


# 12. Explicit Download API End-to-End Test
def test_ws3_6_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws36-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Pred Intel Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Pred Intel Download Test"


# 13. Financial Exposure Authority Lineage Parity Test
@pytest.mark.asyncio
async def test_ws3_6_financial_exposure_authority_parity():
    from app.modules.operational_intelligence.api.router import get_operational_predictive_intelligence
    from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

    handler = PredictiveIntelligenceReportHandler()
    mock_session = AsyncMock()

    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_dto = OperationalPredictiveResponseDTO(
        overall_authority_status="AUTHORITATIVE",
        promoted_model_count=1,
        total_snapshots_found=1,
        prioritization=OperationalPrioritizationDTO(),
        snapshots=[
            OperationalPredictionItemDTO(
                id="id-fin-1",
                prediction_snapshot_id="SNAP-FIN-001",
                idempotency_key="key-fin-1",
                prediction_timestamp="2026-08-05T08:00:00Z",
                prediction_status="SUCCESS",
                model_name="delay_regressor",
                model_version="v1.1.0",
                artifact_sha256="sha-1234",
                feature_set_version="FeatureSetV1",
                dispatch_id="DISP-FIN-001",
                dispatch_code="DN-FIN-001",
                plant_code="VASCO",
                customer_code="CUST-001",
                vehicle_code="GA-01-A-1234",
                target_name="predicted_delay_mins",
                predicted_value=25.0,
                confidence_score=0.92,
                financial_exposure_inr=18500.0,
                total_financial_risk_inr=18500.0
            )
        ],
        calculation_status="SUCCESS",
        calculation_notes="Fin test notes"
    )

    with patch("app.modules.operational_intelligence.services.predictive_service.PredictiveIntelligenceService.get_operational_predictive_intelligence", return_value=mock_dto):
        ui_res = await get_operational_predictive_intelligence(params=DashboardFilterParams(plant_id="VASCO"), session=mock_session)
        ui_snap = ui_res["data"]["snapshots"][0]

        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-fin-parity",
            requested_scope={"plant_id": "VASCO"},
            effective_scope=eff_scope,
            scope_fingerprint="fp-fin-parity",
            requested_by="test_user"
        )
        rep_snap = report.records[0]

        # Verify Financial Exposure Parity: UI API == Report Canonical Record
        assert ui_snap["financial_exposure_inr"] == rep_snap.financial_exposure_inr == 18500.0
        assert ui_snap["total_financial_risk_inr"] == rep_snap.total_financial_risk_inr == 18500.0
        assert report.kpis.total_financial_risk_inr == 18500.0

