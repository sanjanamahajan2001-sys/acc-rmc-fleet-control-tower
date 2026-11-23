import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.dispatch_optimization_canonical import CanonicalDispatchOptimizationReport, ReportMetadataDTO, OptimizationKPISummary
from app.modules.reports.handlers.dispatch_optimization_handler import DispatchOptimizationReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunResponseDTO, OptimizationRunStatusEnum, OptimizationSnapshotMetadataDTO,
    CandidateScenarioDTO, BeforeAfterImpactMatrixDTO, MetricDeltaDTO, OptimizationObjectiveEnum,
    DispatchGanttItemDTO, OptimizationFilterParamsDTO
)

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
        dispatch_id=f"DISP-{i:03d}",
        dispatch_number=f"DN-{i:03d}",
        vehicle_id=f"GA-01-TRUCK-{i:02d}",
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
    for i in range(1, 51)
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

handler = DispatchOptimizationReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine.DispatchOptimizationSolverEngine.execute_optimization_run", return_value=mock_run_resp):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-opt-50", raw_scope, eff_scope, "fp-bench-opt"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_4_DISPATCH_OPTIMIZATION:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
