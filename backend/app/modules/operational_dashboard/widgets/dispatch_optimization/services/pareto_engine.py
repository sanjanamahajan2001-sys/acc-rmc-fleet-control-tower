"""
WS-06.4 Pareto Optimization Engine.
Evaluates candidate scenario proposals across multiple conflicting operational objectives (SLA, DAS, Delay),
filters dominated candidate solutions, and calculates deterministic trade-off scores.
"""

from typing import List, Dict, Any
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    CandidateScenarioDTO,
    BeforeAfterImpactMatrixDTO,
    MetricDeltaDTO,
)


class ParetoOptimizationEngine:
    """Core mathematical engine evaluating Pareto dominance across optimization objectives."""

    @classmethod
    def evaluate_pareto_dominance(
        cls, candidate_vectors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Determines Pareto non-domination for a set of candidate vectors.
        Vector A dominates Vector B if:
          - A is no worse than B in all objectives (SLA gain >= SLA gain, DAS gain >= DAS gain, Delay reduction >= Delay reduction)
          - A is strictly better than B in at least one objective.
        """
        n = len(candidate_vectors)
        results = [dict(v) for v in candidate_vectors]

        for i in range(n):
            is_dominated = False
            dominated_by = []
            for j in range(n):
                if i == j:
                    continue

                a = results[j]
                b = results[i]

                no_worse = (
                    a["sla_gain"] >= b["sla_gain"]
                    and a["das_gain"] >= b["das_gain"]
                    and a["delay_reduction_hrs"] >= b["delay_reduction_hrs"]
                )

                strictly_better = (
                    a["sla_gain"] > b["sla_gain"]
                    or a["das_gain"] > b["das_gain"]
                    or a["delay_reduction_hrs"] > b["delay_reduction_hrs"]
                )

                if no_worse and strictly_better:
                    is_dominated = True
                    dominated_by.append(a["scenario_id"])

            results[i]["is_dominated"] = is_dominated
            results[i]["dominated_by"] = dominated_by

        return results

    @classmethod
    def build_candidate_scenarios(
        cls,
        eval_results: List[Dict[str, Any]],
        baseline_sla: float,
        baseline_das: float,
        baseline_delay_hrs: float,
        baseline_holding_hrs: float,
        baseline_retention_hrs: float,
        baseline_seq_hrs: float,
    ) -> List[CandidateScenarioDTO]:
        """
        Converts evaluated candidate vectors into fully compliant CandidateScenarioDTO instances.
        Applies Pareto non-domination filter and secondary ranking score.
        """
        # 1. Run Pareto non-domination evaluation
        evaluated_vectors = cls.evaluate_pareto_dominance(eval_results)

        # 2. Sort vectors: non-dominated first, then by trade-off score descending
        sorted_vectors = sorted(
            evaluated_vectors,
            key=lambda x: (not x["is_dominated"], x["tradeoff_score"]),
            reverse=True,
        )

        scenarios: List[CandidateScenarioDTO] = []
        for idx, vec in enumerate(sorted_vectors):
            opt_sla = max(0.0, min(100.0, baseline_sla + vec["sla_gain"]))
            opt_das = max(0.0, min(100.0, baseline_das + vec["das_gain"]))
            opt_delay = max(0.0, baseline_delay_hrs - vec["delay_reduction_hrs"])

            opt_holding = max(0.0, baseline_holding_hrs * (1.0 - vec.get("holding_reduction_pct", 0.0)))
            opt_retention = max(0.0, baseline_retention_hrs * (1.0 - vec.get("retention_reduction_pct", 0.0)))
            opt_seq = max(0.0, baseline_seq_hrs * (1.0 - vec.get("seq_reduction_pct", 0.0)))

            sla_delta = opt_sla - baseline_sla
            das_delta = opt_das - baseline_das
            delay_delta = opt_delay - baseline_delay_hrs
            holding_delta = opt_holding - baseline_holding_hrs
            retention_delta = opt_retention - baseline_retention_hrs
            seq_delta = opt_seq - baseline_seq_hrs

            impact_matrix = BeforeAfterImpactMatrixDTO(
                sla_compliance=MetricDeltaDTO(
                    metric_name="SLA Compliance Rate",
                    observed_baseline=round(baseline_sla, 1),
                    optimized_value=round(opt_sla, 1),
                    net_delta=round(sla_delta, 1),
                    percentage_change=round((sla_delta / baseline_sla * 100.0) if baseline_sla > 0 else 0.0, 1),
                    unit="%",
                ),
                dispatch_accuracy_das=MetricDeltaDTO(
                    metric_name="Dispatch Accuracy Score (DAS)",
                    observed_baseline=round(baseline_das, 1),
                    optimized_value=round(opt_das, 1),
                    net_delta=round(das_delta, 1),
                    percentage_change=round((das_delta / baseline_das * 100.0) if baseline_das > 0 else 0.0, 1),
                    unit="%",
                ),
                cumulative_delay_hours=MetricDeltaDTO(
                    metric_name="Total Operational Delay",
                    observed_baseline=round(baseline_delay_hrs, 1),
                    optimized_value=round(opt_delay, 1),
                    net_delta=round(delay_delta, 1),
                    percentage_change=round((delay_delta / baseline_delay_hrs * 100.0) if baseline_delay_hrs > 0 else 0.0, 1),
                    unit="hrs",
                ),
                plant_holding_delay_hours=MetricDeltaDTO(
                    metric_name="Plant Holding Delay (T2a)",
                    observed_baseline=round(baseline_holding_hrs, 1),
                    optimized_value=round(opt_holding, 1),
                    net_delta=round(holding_delta, 1),
                    percentage_change=round((holding_delta / baseline_holding_hrs * 100.0) if baseline_holding_hrs > 0 else 0.0, 1),
                    unit="hrs",
                ),
                site_retention_delay_hours=MetricDeltaDTO(
                    metric_name="Customer Retention Delay (T2c)",
                    observed_baseline=round(baseline_retention_hrs, 1),
                    optimized_value=round(opt_retention, 1),
                    net_delta=round(retention_delta, 1),
                    percentage_change=round((retention_delta / baseline_retention_hrs * 100.0) if baseline_retention_hrs > 0 else 0.0, 1),
                    unit="hrs",
                ),
                sequence_variance_delay_hours=MetricDeltaDTO(
                    metric_name="Sequence Variance Penalty",
                    observed_baseline=round(baseline_seq_hrs, 1),
                    optimized_value=round(opt_seq, 1),
                    net_delta=round(seq_delta, 1),
                    percentage_change=round((seq_delta / baseline_seq_hrs * 100.0) if baseline_seq_hrs > 0 else 0.0, 1),
                    unit="hrs",
                ),
            )

            is_recommended = idx == 0

            scenarios.append(
                CandidateScenarioDTO(
                    scenario_id=vec["scenario_id"],
                    scenario_name=vec["scenario_name"],
                    objective_type=vec["objective_type"],
                    pareto_score=round(vec["tradeoff_score"], 1),
                    is_recommended=is_recommended,
                    impact_matrix=impact_matrix,
                    constraint_violations_count=vec.get("violations_count", 0),
                    constraint_notes=vec.get("constraint_notes", []),
                    gantt_items=vec.get("gantt_items", []),
                )
            )

        return scenarios
