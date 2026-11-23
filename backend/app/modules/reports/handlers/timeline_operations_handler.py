from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.timeline_operations_canonical import (
    CanonicalTimelineOperationsReport,
    ReportMetadataDTO,
    TimelineOperationsKPISummary,
    TimelineEventRecord,
)
from app.modules.operational_dashboard.widgets.timeline_replay.service import TimelineReplayService


import logging

logger = logging.getLogger("timeline_operations_handler")


class TimelineOperationsReportHandler:
    """Handler for assembling canonical Timeline Operations reports from TimelineReplayService."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalTimelineOperationsReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="timeline_operations",
            report_name="Timeline Operations Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            plant_id = effective_scope.get("plant_id", "ALL")
            customer_id = effective_scope.get("customer_id", "ALL")
            dataset_id = effective_scope.get("resolved_dataset_id")

            logger.info(f"Building timeline_operations report for plant={plant_id}, customer={customer_id}")

            dispatch_list = await TimelineReplayService.list_replay_dispatches(
                session=session,
                plant_id=plant_id,
                customer_id=customer_id,
                dataset_id=None,
                page=1,
                page_size=500
            )

            dispatches = dispatch_list.items
            logger.info(f"TimelineReplayService returned {len(dispatches)} dispatches.")

            records = []
            dispatches_with_telemetry = sum(1 for d in dispatches if d.has_telemetry)
            complete_duration_cnt = 0

            for d in dispatches:
                try:
                    d_uuid = UUID(d.dispatch_id) if isinstance(d.dispatch_id, str) else d.dispatch_id
                    detail = await TimelineReplayService.get_dispatch_timeline_detail(
                        session=session,
                        dispatch_id=d_uuid,
                        plant_id="ALL",
                        customer_id="ALL",
                        dataset_id=None
                    )

                    if detail.duration_summary and getattr(detail.duration_summary, "duration_completeness", None) and str(getattr(detail.duration_summary, "duration_completeness", "")).endswith("COMPLETE"):
                        complete_duration_cnt += 1

                    disp_date_str = d.dispatch_date.strftime("%Y-%m-%d") if hasattr(d.dispatch_date, "strftime") else str(d.dispatch_date).split("T")[0]

                    for idx, ev in enumerate(detail.lifecycle_events, start=1):
                        records.append(
                            TimelineEventRecord(
                                event_id=f"{d.dispatch_id}-EV-{idx:02d}",
                                event_type=ev.event_type,
                                authority_type=ev.authority_type.value if hasattr(ev.authority_type, "value") else str(ev.authority_type),
                                timestamp=ev.timestamp.isoformat() if ev.timestamp and hasattr(ev.timestamp, "isoformat") else disp_date_str,
                                duration_mins=ev.duration_mins if ev.duration_mins is not None else 0.0,
                                location_name=ev.location_name,
                                is_inferred_estimate=ev.is_inferred_estimate,
                                notes=ev.notes,
                                dispatch_id=str(d.dispatch_id),
                                dispatch_number=d.dispatch_number,
                                plant_id=d.plant_id,
                                customer_id=d.customer_id,
                                vehicle_id=d.vehicle_id if d.vehicle_id else "N/A",
                                status=d.status
                            )
                        )
                except Exception as ex:
                    logger.warning(f"Failed loading timeline detail for dispatch {d.dispatch_id}: {ex}")
                    continue

            total_events = len(records)
            logger.info(f"Built total {total_events} timeline records across {len(dispatches)} dispatches.")

            kpis = TimelineOperationsKPISummary(
                total_dispatches=len(dispatches),
                total_timeline_events=total_events,
                dispatches_with_telemetry=dispatches_with_telemetry,
                complete_duration_count=complete_duration_cnt
            )

            status = ReportStatus.COMPLETED if (total_events > 0 or len(dispatches) > 0) else ReportStatus.NO_DATA

            return CanonicalTimelineOperationsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=total_events,
                kpis=kpis,
                records=records,
                exceptions=[]
            )
        except Exception as e:
            logger.error(f"Error in TimelineOperationsReportHandler: {e}", exc_info=True)
            return CanonicalTimelineOperationsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=TimelineOperationsKPISummary(),
                records=[],
                exceptions=[]
            )

