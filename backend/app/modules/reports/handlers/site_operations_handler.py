from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus

from app.modules.reports.schemas.site_operations_canonical import (
    CanonicalSiteOperationsReport,
    ReportMetadataDTO,
    SiteOperationsKPIs,
    DelayDistributionRecord,
    SiteInsightRecord,
)
from app.modules.reports.schemas.dispatch_analysis_canonical import DispatchAnalysisRecord
from app.modules.site_dashboard.widgets.site_performance.service import SitePerformanceService
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.cadence_engine import DispatchCadenceEngine



class SiteOperationsReportHandler:

    """Handler for assembling canonical Site Operations reports from SitePerformanceService."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalSiteOperationsReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="site_operations",
            report_name="Site Operations Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            perf_dto = await SitePerformanceService.get_site_performance(session, effective_scope)
            summary = perf_dto.summary

            kpis = SiteOperationsKPIs(
                total_dispatches=summary.total_dispatches,
                within_sla_count=summary.within_sla_count,
                outside_sla_count=summary.outside_sla_count,
                compliance_pct=summary.compliance_pct,
                violation_pct=summary.violation_pct,
                avg_holding_mins=summary.avg_holding_mins,
                percentile_95_holding_mins=summary.percentile_95_holding_mins,
                max_holding_mins=summary.max_holding_mins,
                avg_retention_mins=summary.avg_retention_mins,
                max_retention_mins=summary.max_retention_mins,
                avg_site_time_mins=summary.avg_site_time_mins,
            )

            delays = [
                DelayDistributionRecord(severity=d.severity, count=d.count, percentage=d.percentage)
                for d in perf_dto.delay_distribution
            ]

            insights = [
                SiteInsightRecord(
                    category=i.category,
                    title=i.title,
                    impact_level=i.impact_level,
                    insight_text=i.insight_text
                )
                for i in perf_dto.insights
            ]

            # Populate operational record dispatches using TMDetailsRepository
            records = []
            try:
                from app.modules.site_dashboard.widgets.tm_details.repository import TMDetailsRepository
                from app.modules.site_dashboard.widgets.tm_details.calculations import TMDetailsCalculations

                raw_rows, _ = await TMDetailsRepository.get_filtered_dispatches(session, effective_scope, page=1, page_size=500)
                for idx, r in enumerate(raw_rows, start=1):
                    parsed = TMDetailsCalculations.classify_dispatch(r)
                    records.append({
                        "dispatch_id": str(r.get("dispatch_id", f"DISP-{idx:04d}")),
                        "dispatch_number": str(r.get("tm_no", f"DISP-{idx:04d}")),
                        "dispatch_date": str(r.get("t0_ticket_timestamp", "2026-08-05")).split("T")[0].split(" ")[0],

                        "plant_id": str(r.get("plant_name") or effective_scope.get("plant_id", "ALL")),
                        "customer_id": str(r.get("customer_name") or effective_scope.get("customer_id", "ALL")),
                        "vehicle_id": str(r.get("vehicle_plate") or "N/A"),
                        "interval_mins": float(parsed.get("holding_mins", 0.0) or 0.0),
                        "variance_mins": 0.0,
                        "holding_mins": float(parsed.get("holding_mins", 0.0) or 0.0),
                        "retention_mins": float(parsed.get("retention_mins", 0.0) or 0.0),
                        "sla_status": str(parsed.get("sla_compliance_status", "WITHIN_SLA")),
                        "trip_status": str(r.get("status", "ACTIVE")),
                        "cadence_recommendation": "MAINTAIN"
                    })
            except Exception as e:
                import logging
                logging.getLogger("site_ops_handler").error(f"Error fetching TM details: {e}")

            status = ReportStatus.COMPLETED if summary.total_dispatches > 0 else ReportStatus.NO_DATA

            return CanonicalSiteOperationsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=len(records) if len(records) > 0 else summary.total_dispatches,
                kpis=kpis,
                delay_distribution=delays,
                insights=insights,
                records=records
            )


        except Exception as exc:
            return CanonicalSiteOperationsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=SiteOperationsKPIs(),
                delay_distribution=[],
                insights=[],
                records=[]
            )

