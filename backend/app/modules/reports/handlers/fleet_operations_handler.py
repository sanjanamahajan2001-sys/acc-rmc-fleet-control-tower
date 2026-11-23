from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.fleet_operations_canonical import (
    CanonicalFleetOperationsReport,
    ReportMetadataDTO,
    FleetOperationsKPIs,
    VehicleProductivityRecord,
    VehicleAlertRecord,
)
from app.modules.site_dashboard.widgets.fleet_utilization.service import FleetUtilizationService


class FleetOperationsReportHandler:
    """Handler for assembling canonical Fleet Operations reports from FleetUtilizationService."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalFleetOperationsReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="fleet_operations",
            report_name="Fleet Operations Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            fleet_dto = await FleetUtilizationService.get_fleet_utilization(session, effective_scope)
            summary = fleet_dto.summary

            kpis = FleetOperationsKPIs(
                total_active_vehicles=summary.total_active_vehicles,
                vehicles_with_dispatches=summary.vehicles_with_dispatches,
                idle_vehicles=summary.idle_vehicles,
                fleet_utilization_pct=summary.fleet_utilization_pct,
                avg_dispatches_per_vehicle=summary.avg_dispatches_per_vehicle,
                avg_cycle_time_mins=summary.avg_cycle_time_mins
            )

            records = [
                VehicleProductivityRecord(
                    vehicle_plate=v.vehicle_plate,
                    dispatch_count=v.dispatch_count,
                    total_volume_m3=v.total_volume_m3,
                    avg_holding_mins=v.avg_holding_mins,
                    avg_unloading_mins=v.avg_unloading_mins,
                    avg_retention_mins=v.avg_retention_mins,
                    utilization_pct=v.utilization_pct,
                    status=v.status
                )
                for v in fleet_dto.top_vehicles
            ]

            alerts = [
                VehicleAlertRecord(
                    vehicle_plate=a.vehicle_plate,
                    alert_type=a.alert_type,
                    severity=a.severity,
                    message=a.message
                )
                for a in fleet_dto.alerts
            ]

            status = ReportStatus.COMPLETED if summary.total_active_vehicles > 0 else ReportStatus.NO_DATA

            return CanonicalFleetOperationsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=len(records),
                kpis=kpis,
                records=records,
                alerts=alerts,
                exceptions=[]
            )
        except Exception:
            return CanonicalFleetOperationsReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=FleetOperationsKPIs(),
                records=[],
                alerts=[],
                exceptions=[]
            )
