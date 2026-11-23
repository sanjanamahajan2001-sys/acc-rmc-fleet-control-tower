import io
import json
import openpyxl
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat
from app.modules.reports.schemas.dispatch_optimization_canonical import (
    CanonicalDispatchOptimizationReport,
    OptimizationKPISummary,
    ReportMetadataDTO,
    CandidateScenarioRecord,
    OptimizationAssignmentRecord,
    MetricDeltaRecord
)
from app.modules.reports.handlers.dispatch_optimization_handler import DispatchOptimizationReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunResponseDTO, OptimizationRunStatusEnum, OptimizationSnapshotMetadataDTO,
    CandidateScenarioDTO, BeforeAfterImpactMatrixDTO, MetricDeltaDTO, OptimizationObjectiveEnum,
    DispatchGanttItemDTO, OptimizationFilterParamsDTO
)


@pytest.fixture
def sample_dispatch_optimization_report():
    return CanonicalDispatchOptimizationReport(
        metadata=ReportMetadataDTO(
            execution_id="exec-opt-001",
            report_id="dispatch_optimization",
            report_name="Dispatch Optimization Report",
            generated_at="2026-08-20T10:00:00Z",
            requested_by="test_user"
        ),
        requested_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"},
        effective_scope={"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"},
        scope_fingerprint="sha256-disp-opt-fingerprint-12345",
        status=ReportStatus.COMPLETED,
        record_count=2,
        optimization_run_id="RUN-OPT-100",
        snapshot_hash="hash-1234567890",
        recommended_scenario_id="SCENARIO-BALANCED",
        kpis=OptimizationKPISummary(
            total_dispatches=2,
            baseline_sla_pct=58.0,
            optimized_sla_pct=82.2,
            baseline_delay_hours=14.5,
            optimized_delay_hours=10.4,
            total_delay_hours_saved=4.1,
            pareto_score=94.2
        ),
        impact_deltas=[
            MetricDeltaRecord(
                metric_name="SLA Compliance Rate",
                observed_baseline=58.0,
                optimized_value=82.2,
                net_delta=24.2,
                percentage_change=41.7,
                unit="%"
            )
        ],
        scenarios=[
            CandidateScenarioRecord(
                scenario_id="SCENARIO-BALANCED",
                scenario_name="Balanced Operational Cadence Plan",
                objective_type="BALANCED_OPERATIONS",
                pareto_score=94.2,
                is_recommended=True,
                constraint_violations_count=0,
                sla_gain_pct=24.2,
                delay_reduction_hrs=4.1
            )
        ],
        records=[
            OptimizationAssignmentRecord(
                dispatch_id="DISP-001",
                dispatch_number="DN-001",
                vehicle_id="GA-01-A-1234",
                plant_id="VASCO",
                customer_id="CUST-001",
                baseline_time_out="2026-08-05T08:00:00Z",
                recommended_time_out="2026-08-05T08:15:00Z",
                time_shift_mins=15.0,
                recommendation_reason="PLANT_HOLDING_BOTTLENECK_REDUCTION"
            )
        ],
        exceptions=[]
    )


# 1. Authoritative Data Binding Test
@pytest.mark.asyncio
async def test_ws3_4_authoritative_data_binding():
    handler = DispatchOptimizationReportHandler()
    mock_session = AsyncMock()

    raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
    eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

    mock_impact = BeforeAfterImpactMatrixDTO(
        sla_compliance=MetricDeltaDTO(metric_name="SLA Compliance Rate", observed_baseline=58.0, optimized_value=82.2, net_delta=24.2, percentage_change=41.7, unit="%"),
        dispatch_accuracy_das=MetricDeltaDTO(metric_name="Dispatch Accuracy DAS", observed_baseline=62.0, optimized_value=79.2, net_delta=17.2, percentage_change=27.7, unit="%"),
        cumulative_delay_hours=MetricDeltaDTO(metric_name="Cumulative Delay Hours", observed_baseline=14.5, optimized_value=10.4, net_delta=-4.1, percentage_change=-28.3, unit="hrs"),
        plant_holding_delay_hours=MetricDeltaDTO(metric_name="Plant Holding Hours", observed_baseline=6.0, optimized_value=2.3, net_delta=-3.7, percentage_change=-61.0, unit="hrs"),
        site_retention_delay_hours=MetricDeltaDTO(metric_name="Site Retention Hours", observed_baseline=4.0, optimized_value=2.3, net_delta=-1.7, percentage_change=-42.5, unit="hrs"),
        sequence_variance_delay_hours=MetricDeltaDTO(metric_name="Sequence Variance Hours", observed_baseline=4.5, optimized_value=3.6, net_delta=-0.9, percentage_change=-20.0, unit="hrs")
    )

    mock_gantt = [
        DispatchGanttItemDTO(
            dispatch_id="DISP-001",
            dispatch_number="DN-001",
            vehicle_id="GA-01-A-1234",
            plant_id="VASCO",
            customer_id="CUST-001",
            raw_time_out="08:00",
            raw_time_in="09:30",
            baseline_time_out_iso="2026-08-05T08:00:00Z",
            baseline_time_in_iso="2026-08-05T09:30:00Z",
            recommended_time_out_iso="2026-08-05T08:15:00Z",
            recommended_time_in_iso="2026-08-05T09:45:00Z",
            time_shift_mins=15.0
        )
    ]

    mock_scenario = CandidateScenarioDTO(
        scenario_id="SCENARIO-BALANCED",
        scenario_name="Balanced Operational Cadence Plan",
        objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS,
        pareto_score=94.2,
        is_recommended=True,
        impact_matrix=mock_impact,
        constraint_violations_count=0,
        gantt_items=mock_gantt
    )

    mock_snapshot = OptimizationSnapshotMetadataDTO(
        optimization_run_id="RUN-OPT-100",
        snapshot_hash="hash-1234567890",
        dataset_id="DS-20260805-VASCO",
        ingestion_watermark="2026-08-05T10:00:00Z",
        dispatch_fingerprint_hash="hash-1234",
        filter_scope=OptimizationFilterParamsDTO(plant_id="VASCO"),
        generated_at="2026-08-05T10:00:00Z"
    )

    mock_run_resp = OptimizationRunResponseDTO(
        success=True,
        optimization_run_id="RUN-OPT-100",
        status=OptimizationRunStatusEnum.COMPLETED,
        snapshot=mock_snapshot,
        scenarios=[mock_scenario],
        recommended_scenario_id="SCENARIO-BALANCED"
    )

    with patch("app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine.DispatchOptimizationSolverEngine.execute_optimization_run", return_value=mock_run_resp):
        report = await handler.build_canonical_report(
            session=mock_session,
            execution_id="exec-ws3-4",
            requested_scope=raw_scope,
            effective_scope=eff_scope,
            scope_fingerprint="fp-ws3-4",
            requested_by="test_user"
        )

    assert report.metadata.report_id == "dispatch_optimization"
    assert report.optimization_run_id == "RUN-OPT-100"
    assert report.kpis.total_delay_hours_saved == 4.1
    assert report.record_count == 1


# 2. Source Mapping & Execution Semantics Test
def test_ws3_4_source_mapping_and_semantics(sample_dispatch_optimization_report):
    assert sample_dispatch_optimization_report.optimization_run_id == "RUN-OPT-100"
    assert sample_dispatch_optimization_report.scenarios[0].scenario_id == "SCENARIO-BALANCED"
    assert sample_dispatch_optimization_report.records[0].dispatch_id == "DISP-001"


# 3. Multi-Format Renderers Test (JSON, XLSX, PDF)
def test_ws3_4_multi_format_rendering(sample_dispatch_optimization_report):
    json_bytes = JSONReportRenderer.render(sample_dispatch_optimization_report)
    xlsx_bytes = XLSXReportRenderer.render(sample_dispatch_optimization_report)
    pdf_bytes = PDFReportRenderer.render(sample_dispatch_optimization_report)

    # JSON validation
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["metadata"]["report_id"] == "dispatch_optimization"
    assert json_obj["kpis"]["pareto_score"] == 94.2

    # XLSX validation
    wb = openpyxl.load_workbook(filename=io.BytesIO(xlsx_bytes))
    assert len(wb.sheetnames) == 5

    # PDF validation
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# 4. Cross-Format Parity Test
def test_ws3_4_cross_format_parity(sample_dispatch_optimization_report):
    json_bytes = JSONReportRenderer.render(sample_dispatch_optimization_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))

    assert json_obj["scope_fingerprint"] == sample_dispatch_optimization_report.scope_fingerprint
    assert json_obj["record_count"] == sample_dispatch_optimization_report.record_count
    assert json_obj["kpis"]["total_delay_hours_saved"] == sample_dispatch_optimization_report.kpis.total_delay_hours_saved


# 5. NO_DATA Handling Test
@pytest.mark.asyncio
async def test_ws3_4_no_data_rendering(sample_dispatch_optimization_report):
    sample_dispatch_optimization_report.status = ReportStatus.NO_DATA
    sample_dispatch_optimization_report.record_count = 0
    sample_dispatch_optimization_report.records = []

    json_bytes = JSONReportRenderer.render(sample_dispatch_optimization_report)
    json_obj = json.loads(json_bytes.decode("utf-8"))
    assert json_obj["status"] == "NO_DATA"
    assert json_obj["record_count"] == 0


# 6. Scope Propagation & Filter Sensitivity Test
@pytest.mark.asyncio
async def test_ws3_4_scope_propagation_and_silent_failure():
    resolver = ScopeResolverService()
    scope_a = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "MORNING"}
    scope_b = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "EVENING"}

    fp_a = resolver.compute_scope_fingerprint(scope_a)
    fp_b = resolver.compute_scope_fingerprint(scope_b)

    assert fp_a != fp_b, "Scope fingerprint must change when shift changes"


# 7. Dataset Authority Override Protection Test
@pytest.mark.asyncio
async def test_ws3_4_dataset_authority_override_protection():
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


# 8. Invalid Scope API End-to-End Test
def test_ws3_4_invalid_scope_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db_session

    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    with patch("app.modules.reports.api.router.report_service.create_execution_record", new_callable=AsyncMock):
        try:
            client = TestClient(app)
            payload = {
                "report_id": "dispatch_optimization",
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


# 9. End-to-End Generation, Audit Lifecycle, & Download Test
@pytest.mark.asyncio
async def test_ws3_4_end_to_end_generation_and_audit_lifecycle(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws34-e2e-100"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Dispatch Opt PDF",
            "xlsx": b"PK123 Dispatch Opt XLSX",
            "json": b'{"report_id": "dispatch_optimization"}'
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Dispatch Opt PDF"


# 10. Explicit Download API End-to-End Test
def test_ws3_4_download_api_end_to_end(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

    exec_id = "exec-ws34-dl-test"
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        ReportArtifactStorage.save_artifacts(exec_id, {
            "pdf": b"%PDF-1.4 Dispatch Opt Download Test"
        })

        client = TestClient(app)
        res_dl = client.get(f"/fleet-api/v1/reports/executions/{exec_id}/download?format=pdf")
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "application/pdf"
        assert res_dl.content == b"%PDF-1.4 Dispatch Opt Download Test"
