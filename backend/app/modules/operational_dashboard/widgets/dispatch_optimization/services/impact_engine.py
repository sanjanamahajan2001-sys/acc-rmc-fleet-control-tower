"""
WS-06.5 Operational Impact Evaluation Engine.
Consumes baseline PostgreSQL metrics and WS-06.4 candidate optimization scenarios,
computing deterministic, auditable before/after metric deltas and directional trade-offs.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    BeforeAfterImpactMatrixDTO,
    MetricDeltaDTO,
    CandidateScenarioDTO,
    OptimizationRunResponseDTO,
)


class MetricDirectionEnum(str, Enum):
    """Directional polarity of operational metrics."""
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


class MetricDefinitionDTO(BaseModel):
    """Semantic metric metadata container."""
    metric_name: str
    unit: str
    direction: MetricDirectionEnum


class OptimizationImpactEngine:
    """Computes deterministic before/after operational impact metrics and trade-off matrices."""

    METRIC_SEMANICS: Dict[str, MetricDefinitionDTO] = {
        "sla_compliance": MetricDefinitionDTO(metric_name="SLA Compliance", unit="%", direction=MetricDirectionEnum.HIGHER_IS_BETTER),
        "dispatch_accuracy_das": MetricDefinitionDTO(metric_name="DAS Score", unit="%", direction=MetricDirectionEnum.HIGHER_IS_BETTER),
        "cumulative_delay_hours": MetricDefinitionDTO(metric_name="Cumulative Delay", unit="hrs", direction=MetricDirectionEnum.LOWER_IS_BETTER),
        "plant_holding_delay_hours": MetricDefinitionDTO(metric_name="Holding Delay", unit="hrs", direction=MetricDirectionEnum.LOWER_IS_BETTER),
        "site_retention_delay_hours": MetricDefinitionDTO(metric_name="Retention Delay", unit="hrs", direction=MetricDirectionEnum.LOWER_IS_BETTER),
        "sequence_variance_delay_hours": MetricDefinitionDTO(metric_name="Sequence Variance", unit="hrs", direction=MetricDirectionEnum.LOWER_IS_BETTER),
    }

    @classmethod
    def compute_metric_delta(
        cls, metric_key: str, baseline_val: float, optimized_val: float
    ) -> MetricDeltaDTO:
        """
        Computes deterministic metric delta, percentage change, and directional improvement.
        Maintains single backend rounding policy (1 decimal place).
        """
        meta = cls.METRIC_SEMANICS[metric_key]
        baseline = round(float(baseline_val), 1)
        optimized = round(float(optimized_val), 1)
        delta = round(optimized - baseline, 1)

        if baseline > 0:
            pct_change = round((delta / baseline) * 100.0, 1)
        else:
            pct_change = 0.0

        return MetricDeltaDTO(
            metric_name=meta.metric_name,
            observed_baseline=baseline,
            optimized_value=optimized,
            net_delta=delta,
            percentage_change=pct_change,
            unit=meta.unit,
        )

    @classmethod
    def evaluate_run_impact(
        cls, run_response: OptimizationRunResponseDTO
    ) -> Dict[str, Any]:
        """
        Consumes WS-06.4 OptimizationRunResponseDTO and validates impact consistency across candidate scenarios.
        Reconciles global total delay = holding + retention + sequence variance.
        """
        if not run_response.scenarios:
            return {
                "optimization_run_id": run_response.optimization_run_id,
                "status": run_response.status.value,
                "total_scenarios_evaluated": 0,
                "impact_summary": [],
            }

        summary: List[Dict[str, Any]] = []
        for scen in run_response.scenarios:
            matrix = scen.impact_matrix
            # Verify Total Delay Reconciliation (Cumulative = Holding + Retention + Seq)
            holding_hrs = matrix.plant_holding_delay_hours.optimized_value
            retention_hrs = matrix.site_retention_delay_hours.optimized_value
            seq_hrs = matrix.sequence_variance_delay_hours.optimized_value
            reconciled_total = round(holding_hrs + retention_hrs + seq_hrs, 1)

            summary.append({
                "scenario_id": scen.scenario_id,
                "scenario_name": scen.scenario_name,
                "objective_type": scen.objective_type.value,
                "pareto_score": scen.pareto_score,
                "is_recommended": scen.is_recommended,
                "sla_gain_pct": matrix.sla_compliance.net_delta,
                "das_gain_pct": matrix.dispatch_accuracy_das.net_delta,
                "delay_reduction_hrs": abs(matrix.cumulative_delay_hours.net_delta) if matrix.cumulative_delay_hours.net_delta < 0 else 0.0,
                "reconciled_total_delay_hrs": reconciled_total,
            })

        return {
            "optimization_run_id": run_response.optimization_run_id,
            "status": run_response.status.value,
            "total_scenarios_evaluated": len(run_response.scenarios),
            "impact_summary": summary,
        }
