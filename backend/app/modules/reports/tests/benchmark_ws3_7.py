import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.action_execution_canonical import CanonicalActionExecutionReport, ReportMetadataDTO, ActionExecutionKPISummary
from app.modules.reports.handlers.action_execution_handler import ActionExecutionReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_intelligence.schemas.action_execution_dtos import (
    ActionQueueResponseDTO, ActionLogDTO, ActionStatusEnum, DispatcherRoleEnum
)

mock_dto = ActionQueueResponseDTO(
    items=[
        ActionLogDTO(
            action_id=f"ACT-{i:03d}",
            recommendation_id=f"REC-{i:03d}",
            prediction_snapshot_id=f"SNAP-{i:03d}",
            model_family="delay_regressor",
            model_version="v1.1.0",
            dataset_id="DS-20260805-VASCO",
            operation_date="2026-08-05",
            plant_code="VASCO",
            customer_code="CUST-001",
            dispatch_id=f"DISP-{i:03d}",
            dispatch_code=f"DN-{i:03d}",
            action_type="REROUTE_TRUCK",
            action_parameters={"new_route": "HW4A"},
            predicted_risk_exposure_inr=25000.0,
            estimated_avoided_exposure_inr=25000.0,
            actual_avoided_loss_inr=25000.0,
            action_status=ActionStatusEnum.EXECUTED if i % 2 == 0 else ActionStatusEnum.PENDING,
            dispatcher_id="DISPATCHER_USER_1",
            dispatcher_role=DispatcherRoleEnum.DISPATCHER,
            decision_timestamp="2026-08-05T08:00:00Z",
            execution_confirmed_at="2026-08-05T08:30:00Z",
            reason_code="TRAFFIC_CONGESTION_BYPASS",
            dispatcher_notes="Rerouted via Highway 4A",
            idempotency_key=f"key-act-{i:03d}",
            version_lock=1
        )
        for i in range(1, 26)
    ],
    total_count=25,
    pending_count=12,
    accepted_count=0,
    executed_count=13
)

handler = ActionExecutionReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.operational_intelligence.services.action_execution_service.ActionExecutionService.get_action_queue", return_value=mock_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-act-25", raw_scope, eff_scope, "fp-bench-act"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_7_ACTION_EXECUTION:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
