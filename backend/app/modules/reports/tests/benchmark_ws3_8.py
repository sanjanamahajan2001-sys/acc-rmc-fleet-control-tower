import time
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.alerts_incidents_canonical import CanonicalAlertsIncidentsReport, ReportMetadataDTO, AlertsIncidentsKPISummary
from app.modules.reports.handlers.alerts_incidents_handler import AlertsIncidentsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_dashboard.widgets.alerts.dtos import (
    AlertListResponseDTO, OperationalAlertItemDTO, AlertSummaryDTO, AlertSeverityEnum, AlertStatusEnum, OperationalDatasetContextDTO
)

mock_list_dto = AlertListResponseDTO(
    items=[
        OperationalAlertItemDTO(
            id=uuid4(),
            alert_fingerprint=f"fingerprint-{i:064d}"[:64],
            alert_type="HIGH_QUEUE_TIME" if i % 2 == 0 else "SLA_BREACH_RISK",
            severity=AlertSeverityEnum.CRITICAL if i % 3 == 0 else AlertSeverityEnum.WARNING,
            status=AlertStatusEnum.OPEN if i % 2 == 0 else AlertStatusEnum.ACKNOWLEDGED,
            plant_id="VASCO",
            customer_id="CUST-001",
            dispatch_id=uuid4(),
            vehicle_id=f"GA-01-A-{i:04d}",
            dataset_id="DS-20260805-VASCO",
            import_job_id=None,
            metric_name="holding_time_mins",
            actual_value=45.0 + i,
            threshold_value=30.0,
            unit="mins",
            business_impact="HIGH_QUEUE_DELAY",
            evidence_json={},
            recommended_action="DISPATCH_NEW_TM",
            detected_at=datetime.now(timezone.utc),
            evaluated_at=datetime.now(timezone.utc),
            rule_version="v1.0.0"
        )
        for i in range(1, 26)
    ],
    total_count=25,
    page=1,
    page_size=50,
    total_pages=1
)

mock_ctx = OperationalDatasetContextDTO(
    operational_date="2026-08-05",
    total_dispatches=100,
    last_imported_at="2026-08-05T00:00:00Z",
    dataset_id="DS-20260805-VASCO"
)

mock_summary_dto = AlertSummaryDTO(
    total_active_alerts=25,
    critical_count=9,
    warning_count=16,
    info_count=0,
    acknowledged_count=12,
    dataset_context=mock_ctx
)

handler = AlertsIncidentsReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.operational_dashboard.widgets.alerts.service.AlertService.get_alerts_list", return_value=mock_list_dto), \
     patch("app.modules.operational_dashboard.widgets.alerts.service.AlertService.get_summary", return_value=mock_summary_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-alt-25", raw_scope, eff_scope, "fp-bench-alt"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_8_ALERTS_INCIDENTS:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
