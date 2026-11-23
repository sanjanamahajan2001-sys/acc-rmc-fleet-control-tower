from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.dispatch_analysis.services.cadence_engine import DispatchCadenceEngine
from app.modules.reports.schemas.dispatch_analysis_canonical import (
    CanonicalDispatchAnalysisReport,
    ReportMetadataDTO,
    DispatchAnalysisKPIs,
    DispatchAnalysisRecord,
    DelayCategoryBreakdown
)
from app.modules.reports.schemas.report_schemas import ReportStatus


class DispatchAnalysisReportHandler:
    @classmethod
    async def build_canonical_report(
        cls,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        requested_by: str = "system",
        status: ReportStatus = ReportStatus.COMPLETED
    ) -> CanonicalDispatchAnalysisReport:
        cadence_engine = DispatchCadenceEngine


        plant_id = effective_scope.get("plant_id", "ALL")
        customer_id = effective_scope.get("customer_id", "ALL")
        operation_date = effective_scope.get("operation_date")
        shift = effective_scope.get("shift", "ALL")

        # Query operational engine methods
        kpis_dto = await cadence_engine.get_kpis(
            session=session,
            filters=effective_scope
        )
        cadence_table_dto = await cadence_engine.get_cadence_table(
            session=session,
            filters=effective_scope
        )
        delay_analytics_dto = await cadence_engine.get_delay_analytics(
            session=session,
            filters=effective_scope
        )
        insights_dto = await cadence_engine.get_operational_insights(
            session=session,
            filters=effective_scope
        )

        kpis_data = kpis_dto.data.model_dump() if hasattr(kpis_dto, "data") and kpis_dto.data else (kpis_dto.get("data") or {}) if isinstance(kpis_dto, dict) else {}
        cadence_table = cadence_table_dto.data if hasattr(cadence_table_dto, "data") and cadence_table_dto.data else (cadence_table_dto.get("data", []) if isinstance(cadence_table_dto, dict) else [])
        delay_analytics = delay_analytics_dto.data.model_dump() if hasattr(delay_analytics_dto, "data") and delay_analytics_dto.data else (delay_analytics_dto.get("data") or {}) if isinstance(delay_analytics_dto, dict) else {}
        insights_data = insights_dto.data if hasattr(insights_dto, "data") and insights_dto.data else (insights_dto.get("data", []) if isinstance(insights_dto, dict) else [])


        records = []
        for i, row_item in enumerate(cadence_table, start=1):
            row = row_item.model_dump() if hasattr(row_item, "model_dump") else (row_item if isinstance(row_item, dict) else {})
            records.append(
                DispatchAnalysisRecord(
                    dispatch_id=str(row.get("dispatch_id", f"disp_{i}")),
                    dispatch_number=str(row.get("dispatch_number", f"DISP-{i:03d}")),
                    dispatch_date=str(row.get("dispatch_date", operation_date or "")),
                    time_out=row.get("time_out"),
                    time_in=row.get("time_in"),
                    plant_code=str(row.get("plant_code", plant_id)),
                    customer_code=str(row.get("customer_code", customer_id)),
                    customer_name=str(row.get("customer_name", "N/A")),
                    vehicle_id=str(row.get("vehicle_id", "N/A")),
                    driver_name=str(row.get("driver_name", "N/A")),
                    interval_mins=float(row.get("interval_mins", 0.0)),
                    variance_mins=float(row.get("variance_mins", 0.0)),
                    holding_mins=float(row.get("holding_mins", 0.0)),
                    retention_mins=float(row.get("retention_mins", 0.0)),
                    sla_status=str(row.get("sla_status", "NON_COMPLIANT")),
                    trip_status=str(row.get("trip_status", "IN_TRANSIT")),
                    cadence_recommendation=str(row.get("cadence_recommendation", "MAINTAIN"))
                )
            )


        raw_cats = delay_analytics.get("categories", []) if isinstance(delay_analytics, dict) else (getattr(delay_analytics, "categories", []) or [])
        delay_categories = []
        for cat_item in raw_cats:
            cat = cat_item.model_dump() if hasattr(cat_item, "model_dump") else (cat_item if isinstance(cat_item, dict) else {})
            delay_categories.append(
                DelayCategoryBreakdown(
                    category_name=str(cat.get("category_name", "Uncategorized")),
                    delay_hours=float(cat.get("delay_hours", 0.0)),
                    percentage_contribution=float(cat.get("percentage_contribution", 0.0)),
                    affected_trips_count=int(cat.get("affected_trips_count", 0)),
                    severity=str(cat.get("severity", "MEDIUM")),
                    recommendation=str(cat.get("recommendation", "Review process"))
                )
            )

        insights = []
        raw_insights = insights_data if isinstance(insights_data, list) else []
        for ins in raw_insights:
            if hasattr(ins, "insight_text"):
                insights.append(str(ins.insight_text))
            elif isinstance(ins, dict):
                insights.append(str(ins.get("insight_text", str(ins))))
            else:
                insights.append(str(ins))


        return CanonicalDispatchAnalysisReport(
            metadata=ReportMetadataDTO(
                execution_id=execution_id,
                report_id="dispatch_analysis",
                report_name="Dispatch Analysis Report",
                requested_by=requested_by
            ),
            requested_scope=requested_scope,
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            status=status,
            record_count=len(records),
            kpis=DispatchAnalysisKPIs(
                total_dispatches=int(kpis_data.get("total_dispatches", 0)),
                on_schedule_dispatches=int(kpis_data.get("on_schedule_dispatches", 0)),
                sla_compliance_pct=float(kpis_data.get("sla_compliance_pct", 0.0)),
                avg_interval_mins=float(kpis_data.get("avg_interval_mins", 0.0)),
                interval_variance_mins=float(kpis_data.get("interval_variance_mins", 0.0)),
                das_score_pct=float(kpis_data.get("das_score_pct", 0.0)),
                completed_dispatches=int(kpis_data.get("completed_dispatches", 0)),
                avg_loading_mins=float(kpis_data.get("avg_loading_mins", 0.0)),
                avg_transit_mins=float(kpis_data.get("avg_transit_mins", 0.0)),
                recommended_interval_mins=float(kpis_data.get("recommended_interval_mins", 15.0)),
                cadence_status=str(kpis_data.get("cadence_status", "OPTIMAL")),
                potential_delay_reduction_hrs=float(kpis_data.get("potential_delay_reduction_hrs", 0.0))
            ),
            records=records,
            delay_categories=delay_categories,
            insights=insights
        )
