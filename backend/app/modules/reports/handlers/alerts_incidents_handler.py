from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.alerts_incidents_canonical import (
    CanonicalAlertsIncidentsReport,
    ReportMetadataDTO,
    AlertsIncidentsKPISummary,
    OperationalAlertRecord,
)
from app.modules.operational_dashboard.widgets.alerts.service import AlertService


class AlertsIncidentsReportHandler:
    """Handler for assembling canonical Alerts & Incidents reports from AlertService."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalAlertsIncidentsReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="alerts_incidents",
            report_name="Alerts & Incidents Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            plant_id = effective_scope.get("plant_id", "ALL")
            customer_id = effective_scope.get("customer_id", "ALL")
            dataset_id = effective_scope.get("resolved_dataset_id")

            alerts_list = await AlertService.get_alerts_list(
                session=session,
                plant_id=plant_id,
                customer_id=customer_id,
                dataset_id=None,
                page=1,
                page_size=500
            )

            summary = await AlertService.get_summary(
                session=session,
                plant_id=plant_id,
                customer_id=customer_id,
                dataset_id=None
            )

            items = alerts_list.items


            records = [
                OperationalAlertRecord(
                    alert_id=str(item.id),
                    alert_fingerprint=item.alert_fingerprint,
                    alert_type=item.alert_type,
                    severity=item.severity.value if hasattr(item.severity, "value") else str(item.severity),
                    status=item.status.value if hasattr(item.status, "value") else str(item.status),
                    plant_id=item.plant_id,
                    customer_id=item.customer_id,
                    dispatch_id=str(item.dispatch_id) if item.dispatch_id else None,
                    vehicle_id=item.vehicle_id,
                    dataset_id=item.dataset_id,
                    metric_name=item.metric_name,
                    actual_value=item.actual_value,
                    threshold_value=item.threshold_value,
                    unit=item.unit,
                    business_impact=item.business_impact,
                    recommended_action=item.recommended_action,
                    evidence_json=item.evidence_json if isinstance(item.evidence_json, dict) else {},
                    detected_at=item.detected_at.isoformat() if hasattr(item.detected_at, "isoformat") else str(item.detected_at),
                    evaluated_at=item.evaluated_at.isoformat() if hasattr(item.evaluated_at, "isoformat") else str(item.evaluated_at),
                    acknowledged_at=item.acknowledged_at.isoformat() if item.acknowledged_at and hasattr(item.acknowledged_at, "isoformat") else (str(item.acknowledged_at) if item.acknowledged_at else None),
                    acknowledged_by=item.acknowledged_by,
                    resolved_at=item.resolved_at.isoformat() if item.resolved_at and hasattr(item.resolved_at, "isoformat") else (str(item.resolved_at) if item.resolved_at else None),
                    resolved_by=item.resolved_by,
                    resolution_reason=item.resolution_reason,
                    rule_version=item.rule_version
                )
                for item in items
            ]


            total_alerts = len(records)

            kpis = AlertsIncidentsKPISummary(
                total_active_alerts=summary.total_active_alerts,
                critical_count=summary.critical_count,
                warning_count=summary.warning_count,
                info_count=summary.info_count,
                acknowledged_count=summary.acknowledged_count
            )

            status = ReportStatus.COMPLETED if total_alerts > 0 else ReportStatus.NO_DATA

            return CanonicalAlertsIncidentsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=total_alerts,
                kpis=kpis,
                records=records,
                exceptions=[]
            )
        except Exception:
            return CanonicalAlertsIncidentsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=AlertsIncidentsKPISummary(),
                records=[],
                exceptions=[]
            )
