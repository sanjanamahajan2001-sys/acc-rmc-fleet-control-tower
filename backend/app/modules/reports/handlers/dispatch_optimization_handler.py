from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.dispatch_optimization_canonical import (
    CanonicalDispatchOptimizationReport,
    ReportMetadataDTO,
    OptimizationKPISummary,
    MetricDeltaRecord,
    CandidateScenarioRecord,
    OptimizationAssignmentRecord,
)
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import DispatchOptimizationSolverEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunRequestDTO,
    OptimizationFilterParamsDTO,
    ObjectiveConfigDTO,
    OptimizationObjectiveEnum,
)


class DispatchOptimizationReportHandler:
    """Handler for assembling canonical Dispatch Optimization reports from DispatchOptimizationSolverEngine."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalDispatchOptimizationReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="dispatch_optimization",
            report_name="Dispatch Optimization Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            filters_dto = OptimizationFilterParamsDTO(
                plant_id=effective_scope.get("plant_id", "ALL"),
                customer_id=effective_scope.get("customer_id", "ALL"),
                dataset_type=effective_scope.get("dataset_type", "REAL_ONLY")
            )
            run_req = OptimizationRunRequestDTO(
                filters=filters_dto,
                objective_config=ObjectiveConfigDTO(
                    objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS
                )
            )

            run_resp = await DispatchOptimizationSolverEngine.execute_optimization_run(session, run_req)

            if not run_resp.scenarios or run_resp.status.value in ["NO_FEASIBLE_SOLUTION", "FAILED"]:
                return CanonicalDispatchOptimizationReport(
                    metadata=metadata,
                    requested_scope=requested_scope,
                    effective_scope=effective_scope,
                    scope_fingerprint=scope_fingerprint,
                    status=ReportStatus.NO_DATA,
                    record_count=0,
                    optimization_run_id=run_resp.optimization_run_id or "",
                    snapshot_hash="",
                    recommended_scenario_id="",
                    kpis=OptimizationKPISummary(),
                    impact_deltas=[],
                    scenarios=[],
                    records=[],
                    exceptions=[]
                )

            scenarios_list = [
                CandidateScenarioRecord(
                    scenario_id=sc.scenario_id,
                    scenario_name=sc.scenario_name,
                    objective_type=sc.objective_type.value if hasattr(sc.objective_type, "value") else str(sc.objective_type),
                    pareto_score=sc.pareto_score,
                    is_recommended=sc.is_recommended,
                    constraint_violations_count=sc.constraint_violations_count,
                    sla_gain_pct=sc.impact_matrix.sla_compliance.net_delta,
                    delay_reduction_hrs=abs(sc.impact_matrix.cumulative_delay_hours.net_delta)
                )
                for sc in run_resp.scenarios
            ]

            rec_sc = next((sc for sc in run_resp.scenarios if sc.is_recommended), run_resp.scenarios[0])
            impact = rec_sc.impact_matrix

            kpis = OptimizationKPISummary(
                total_dispatches=len(rec_sc.gantt_items),
                baseline_sla_pct=impact.sla_compliance.observed_baseline,
                optimized_sla_pct=impact.sla_compliance.optimized_value,
                baseline_delay_hours=impact.cumulative_delay_hours.observed_baseline,
                optimized_delay_hours=impact.cumulative_delay_hours.optimized_value,
                total_delay_hours_saved=abs(impact.cumulative_delay_hours.net_delta),
                pareto_score=rec_sc.pareto_score
            )

            impact_deltas = [
                MetricDeltaRecord(
                    metric_name=m.metric_name,
                    observed_baseline=m.observed_baseline,
                    optimized_value=m.optimized_value,
                    net_delta=m.net_delta,
                    percentage_change=m.percentage_change,
                    unit=m.unit
                )
                for m in [
                    impact.sla_compliance,
                    impact.dispatch_accuracy_das,
                    impact.cumulative_delay_hours,
                    impact.plant_holding_delay_hours,
                    impact.site_retention_delay_hours
                ]
            ]

            assignments = [
                OptimizationAssignmentRecord(
                    dispatch_id=g.dispatch_id,
                    dispatch_number=g.dispatch_number,
                    vehicle_id=g.vehicle_id,
                    plant_id=g.plant_id,
                    customer_id=g.customer_id,
                    baseline_time_out=g.baseline_time_out_iso,
                    recommended_time_out=g.recommended_time_out_iso,
                    time_shift_mins=g.time_shift_mins,
                    recommendation_reason=g.recommendation_reason.explanation if g.recommendation_reason else "OPTIMAL_CADENCE"
                )
                for g in rec_sc.gantt_items
            ]

            status = ReportStatus.COMPLETED if len(assignments) > 0 else ReportStatus.NO_DATA

            return CanonicalDispatchOptimizationReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=len(assignments),
                optimization_run_id=run_resp.optimization_run_id,
                snapshot_hash=run_resp.snapshot.snapshot_hash if run_resp.snapshot else "",
                recommended_scenario_id=run_resp.recommended_scenario_id or rec_sc.scenario_id,
                kpis=kpis,
                impact_deltas=impact_deltas,
                scenarios=scenarios_list,
                records=assignments,
                exceptions=[]
            )
        except Exception:
            return CanonicalDispatchOptimizationReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                optimization_run_id="",
                snapshot_hash="",
                recommended_scenario_id="",
                kpis=OptimizationKPISummary(),
                impact_deltas=[],
                scenarios=[],
                records=[],
                exceptions=[]
            )
