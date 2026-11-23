from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.site_comparison_canonical import (
    CanonicalSiteComparisonReport,
    ReportMetadataDTO,
    SiteComparisonKPISummary,
    SiteComparisonRecord,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_comparison import SiteComparisonEngine


class SiteComparisonReportHandler:
    """Handler for assembling canonical Site Comparison reports from SiteComparisonEngine."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalSiteComparisonReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="site_comparison",
            report_name="Site Comparison Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            comparison_dto = await SiteComparisonEngine.get_site_comparison(session, effective_scope)
            site_list = comparison_dto.data

            records = [
                SiteComparisonRecord(
                    rank=s.rank,
                    site_code=s.site_code,
                    site_name=s.site_name,
                    dispatches=s.dispatches,
                    volume_cum=s.volume_cum,
                    avg_holding_mins=s.avg_holding_mins,
                    avg_retention_mins=s.avg_retention_mins,
                    max_queue_tms=s.max_queue_tms,
                    dispatch_accuracy=s.dispatch_accuracy,
                    status=s.status
                )
                for s in site_list
            ]

            total_sites = len(records)
            total_disp = sum(r.dispatches for r in records)
            total_vol = round(sum(r.volume_cum for r in records), 1)
            avg_hold = round(sum(r.avg_holding_mins for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            avg_ret = round(sum(r.avg_retention_mins for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            avg_das = round(sum(r.dispatch_accuracy for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            optimal_cnt = sum(1 for r in records if r.status == "Optimal")

            kpis = SiteComparisonKPISummary(
                total_sites_evaluated=total_sites,
                total_dispatches=total_disp,
                total_volume_cum=total_vol,
                avg_holding_mins=avg_hold,
                avg_retention_mins=avg_ret,
                avg_dispatch_accuracy=avg_das,
                optimal_sites_count=optimal_cnt
            )

            status = ReportStatus.COMPLETED if total_sites > 0 else ReportStatus.NO_DATA

            return CanonicalSiteComparisonReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=total_sites,
                kpis=kpis,
                records=records,
                exceptions=[]
            )
        except Exception:
            return CanonicalSiteComparisonReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=SiteComparisonKPISummary(),
                records=[],
                exceptions=[]
            )
