from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.erp_data_explorer_canonical import (
    CanonicalERPDataExplorerReport,
    ReportMetadataDTO,
    ERPDataExplorerKPISummary,
    ERPDispatchRecord,
)
from app.modules.erp.models import Plant, Customer, Dispatch
from app.modules.erp.api.explorer import _generic_explorer_query


class ERPDataExplorerReportHandler:
    """Handler for assembling canonical ERP Data Reports from ERP Explorer APIs/Queries."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalERPDataExplorerReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="erp_data_explorer",
            report_name="ERP Data Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            # Query canonical aggregates
            total_plants = (await session.execute(select(func.count()).select_from(Plant))).scalar_one() or 0
            total_custs = (await session.execute(select(func.count()).select_from(Customer))).scalar_one() or 0

            # Fetch enriched dispatches using existing authoritative explorer query logic
            dispatch_dicts, total_dispatches = await _generic_explorer_query(
                Dispatch, session, page=1, page_size=50
            )

            records = [
                ERPDispatchRecord(
                    dispatch_id=str(d.get("id")),
                    dispatch_number=str(d.get("dispatch_number", "N/A")),
                    plant_name=d.get("plant_name"),
                    customer_name=d.get("customer_name"),
                    vehicle_code=d.get("vehicle_code"),
                    status=str(d.get("status", "ACTIVE")),
                    telemetry_status=str(d.get("telemetry_status", "PENDING_CORRELATION")),
                    correlation_score=str(d.get("correlation_score")) if d.get("correlation_score") is not None else None,
                    time_out=d.get("time_out").isoformat() if d.get("time_out") and hasattr(d.get("time_out"), "isoformat") else (str(d.get("time_out")) if d.get("time_out") else None),
                    time_in=d.get("time_in").isoformat() if d.get("time_in") and hasattr(d.get("time_in"), "isoformat") else (str(d.get("time_in")) if d.get("time_in") else None),
                    cycle_time=float(d["cycle_time"]) if isinstance(d.get("cycle_time"), (int, float)) else None

                )
                for d in dispatch_dicts
            ]

            corr_cnt = sum(1 for r in records if r.telemetry_status == "CORRELATED")

            kpis = ERPDataExplorerKPISummary(
                total_plants=total_plants,
                total_customers=total_custs,
                total_dispatches=total_dispatches,
                correlated_dispatches_count=corr_cnt
            )

            status = ReportStatus.COMPLETED if len(records) > 0 else ReportStatus.NO_DATA

            return CanonicalERPDataExplorerReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=len(records),
                kpis=kpis,
                records=records,
                exceptions=[]
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return CanonicalERPDataExplorerReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=ERPDataExplorerKPISummary(),
                records=[],
                exceptions=[]
            )

