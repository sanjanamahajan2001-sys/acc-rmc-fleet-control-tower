import time
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.modules.reports.schemas.timeline_operations_canonical import CanonicalTimelineOperationsReport, ReportMetadataDTO, TimelineOperationsKPISummary
from app.modules.reports.handlers.timeline_operations_handler import TimelineOperationsReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    DispatchReplayListResponseDTO, DispatchReplayListItemDTO, DispatchTimelineReplayDetailDTO,
    TimelineEventItemDTO, EventAuthorityEnum, DurationSummaryDTO, DurationCompletenessEnum,
    TelemetrySummaryDTO, SpatialContextDTO, SpatialModeEnum
)

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
        TimelineEventItemDTO(event_type="Batched", authority_type=EventAuthorityEnum.DIRECT, timestamp=datetime.now(timezone.utc), duration_mins=0.0, location_name="VASCO Plant"),
        TimelineEventItemDTO(event_type="Departed Plant", authority_type=EventAuthorityEnum.DIRECT, timestamp=datetime.now(timezone.utc), duration_mins=15.0, location_name="VASCO Plant Gate")
    ],
    telemetry_summary=TelemetrySummaryDTO(telemetry_matched=True),
    spatial_context=SpatialContextDTO(has_gps_breadcrumbs=False, spatial_mode=SpatialModeEnum.NO_SPATIAL_DATA)
)

handler = TimelineOperationsReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.operational_dashboard.widgets.timeline_replay.service.TimelineReplayService.list_replay_dispatches", return_value=mock_list_dto), \
     patch("app.modules.operational_dashboard.widgets.timeline_replay.service.TimelineReplayService.get_dispatch_timeline_detail", return_value=mock_detail_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-tl-25", raw_scope, eff_scope, "fp-bench-tl"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_9_TIMELINE_OPERATIONS:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
