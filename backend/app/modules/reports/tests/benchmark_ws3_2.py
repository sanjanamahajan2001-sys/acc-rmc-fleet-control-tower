import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.fleet_operations_canonical import CanonicalFleetOperationsReport, ReportMetadataDTO, FleetOperationsKPIs
from app.modules.reports.handlers.fleet_operations_handler import FleetOperationsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.site_dashboard.widgets.fleet_utilization.dtos import FleetUtilizationResponseDTO, FleetSummaryDTO

mock_dto = FleetUtilizationResponseDTO(
    summary=FleetSummaryDTO(
        total_active_vehicles=100,
        vehicles_with_dispatches=85,
        idle_vehicles=15,
        fleet_utilization_pct=85.0,
        avg_dispatches_per_vehicle=4.2,
        avg_cycle_time_mins=24.5
    ),
    top_vehicles=[],
    alerts=[]
)

handler = FleetOperationsReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.site_dashboard.widgets.fleet_utilization.service.FleetUtilizationService.get_fleet_utilization", return_value=mock_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-fleet-100", raw_scope, eff_scope, "fp-bench-fleet"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_2_FLEET_OPERATIONS:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
