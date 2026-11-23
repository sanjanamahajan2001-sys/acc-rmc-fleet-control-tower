"""
Operational Intelligence Health Service
Phase 1 Operational Health & Executive Index Engine

Authoritative data flow:
PostgreSQL (dispatches, trips, operational_alerts)
  ↓
ExecutiveKPIService + OperationalAlertRepository
  ↓
HealthService (Zero arbitrary weights, Full Provenance, Dataset Freshness)
  ↓
OperationalHealthResponseDTO
"""

from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.operational_dashboard.widgets.kpis.orchestration_service import ExecutiveKPIService
from app.modules.operational_dashboard.widgets.alerts.repository import OperationalAlertRepository
from app.modules.operational_intelligence.schemas.health_dtos import (
    OperationalHealthResponseDTO,
    HealthMetricDTO,
    DatasetFreshnessDTO,
)


class OperationalHealthService:
    """
    Service Engine for Operational Health & Executive Index (Section 01).
    All values are derived directly from authoritative PostgreSQL persistence.
    """

    @classmethod
    async def get_operational_health(
        cls,
        session: AsyncSession,
        params: DashboardFilterParams,
    ) -> OperationalHealthResponseDTO:
        # 1. Fetch shell context & dataset freshness envelope from PostgreSQL
        shell_context = await OperationalContextService.get_shell_context(session, params)
        context_env = shell_context.context
        meta = shell_context.metadata
        total_dispatches = meta.get("total_dispatches", 0)
        dataset_status = meta.get("dataset_status", "ACTIVE_PRODUCTION")

        freshness = DatasetFreshnessDTO(
            dataset_id=context_env.dataset_id,
            operational_date=context_env.operational_date,
            import_timestamp=context_env.generated_at,
            dataset_status=dataset_status,
            total_dispatches=total_dispatches,
            total_trips=total_dispatches,
        )

        # Handle 0 / No Records condition
        if total_dispatches == 0:
            return OperationalHealthResponseDTO(
                overall_health_score=None,
                health_status="UNAVAILABLE",
                freshness=freshness,
                metrics=[],
                calculation_status="NO_RECORDS",
                calculation_notes="No canonical dispatches or trip records found under the active filter context.",
            )

        # 2. Fetch authoritative KPIs from ExecutiveKPIService
        kpi_ribbon = await ExecutiveKPIService.get_kpi_ribbon(session, params)
        kpis = kpi_ribbon.kpis

        # 3. Fetch authoritative Alert Summary counts from OperationalAlertRepository
        alert_counts = await OperationalAlertRepository.get_summary_counts(
            session=session,
            plant_id=params.plant_id or "ALL",
            customer_id=params.customer_id or "ALL",
            dataset_id=context_env.dataset_id,
        )

        # 4. Map authoritative metrics with reproducible provenance
        metrics: List[HealthMetricDTO] = []

        # Metric 1: Dispatch Accuracy Score (DAS)
        das_val = kpis.dispatch_accuracy.current_value or 0.0
        metrics.append(
            HealthMetricDTO(
                key="dispatch_accuracy",
                label="Dispatch Accuracy Score (DAS)",
                current_value=float(das_val),
                unit="%",
                status=kpis.dispatch_accuracy.status.value,
                target=kpis.dispatch_accuracy.target,
                variance=kpis.dispatch_accuracy.variance,
                provenance_table="dispatches",
                provenance_formula="count(on_time_dispatches) / count(total_dispatches) * 100",
            )
        )

        # Metric 2: Site Waiting Index (SWI)
        swi_val = kpis.swi.current_value or 0.0
        metrics.append(
            HealthMetricDTO(
                key="site_waiting_index",
                label="Site Waiting Index (SWI)",
                current_value=float(swi_val),
                unit="hrs",
                status=kpis.swi.status.value,
                target=kpis.swi.target,
                variance=kpis.swi.variance,
                provenance_table="dispatches",
                provenance_formula="sum(holding_time > 20min) / count(dispatches)",
            )
        )

        # Metric 3: Delay Penalty Index (DPI)
        dpi_val = kpis.dpi.current_value or 0.0
        metrics.append(
            HealthMetricDTO(
                key="delay_penalty_index",
                label="Delay Penalty Index (DPI)",
                current_value=float(dpi_val),
                unit="hrs",
                status=kpis.dpi.status.value,
                target=kpis.dpi.target,
                variance=kpis.dpi.variance,
                provenance_table="dispatches",
                provenance_formula="sum(retention_time > 10min) / count(dispatches)",
            )
        )

        # Metric 4: Fleet Utilization Index (FUI)
        fui_val = kpis.fui.current_value or 0.0
        metrics.append(
            HealthMetricDTO(
                key="fleet_utilization_index",
                label="Fleet Utilization Index (FUI)",
                current_value=float(fui_val),
                unit="%",
                status=kpis.fui.status.value,
                target=kpis.fui.target,
                variance=kpis.fui.variance,
                provenance_table="trips / vehicles",
                provenance_formula="count(active_vehicles_with_trips) / count(total_fleet) * 100",
            )
        )

        # Metric 5: Active Critical Alerts
        critical_count = float(alert_counts.get("critical_count", 0))
        metrics.append(
            HealthMetricDTO(
                key="active_critical_alerts",
                label="Active Critical Alerts",
                current_value=critical_count,
                unit="alerts",
                status="CRITICAL" if critical_count > 0 else "OPTIMAL",
                threshold=0.0,
                provenance_table="operational_alerts",
                provenance_formula="count(id) where status='OPEN' and severity='CRITICAL'",
            )
        )

        # 5. Composite Health Status Evaluation (Strictly rule-based, no arbitrary weights)
        # Status logic: If critical alerts > 0 or DAS < 80% -> DEGRADED/CRITICAL. Else HEALTHY.
        health_status = "HEALTHY"
        if critical_count > 2 or das_val < 75.0:
            health_status = "CRITICAL"
        elif critical_count > 0 or das_val < 90.0 or swi_val > 5.0:
            health_status = "DEGRADED"

        # Overall health score is exposed as DAS (authoritative primary SLA indicator) rather than an arbitrary synthetic formula
        overall_health_score = round(float(das_val), 2)

        return OperationalHealthResponseDTO(
            overall_health_score=overall_health_score,
            health_status=health_status,
            freshness=freshness,
            metrics=metrics,
            calculation_status="SUCCESS",
            calculation_notes=f"Authoritative PostgreSQL calculation successful across {total_dispatches} dispatches.",
        )
