"""
Decision Intelligence Recommendation Engine
Workstream 2.9 Recommendation Engine
"""

from typing import Any
from app.modules.site_dashboard.widgets.decision_intelligence.dtos import (
    DecisionSummaryDTO,
    RecommendationRowDTO,
    DecisionInsightCardDTO,
)


class RecommendationEngine:
    """Dynamic rules-based decision intelligence engine evaluating PostgreSQL operational metrics."""

    @staticmethod
    def generate_recommendations(
        raw_metrics: dict[str, Any],
        filters: dict[str, Any]
    ) -> tuple[DecisionSummaryDTO, list[RecommendationRowDTO], list[DecisionInsightCardDTO]]:
        
        dispatches = raw_metrics["total_dispatches"]
        holding_breaches = raw_metrics["holding_breaches"]
        retention_breaches = raw_metrics["retention_breaches"]
        sum_holding = raw_metrics["sum_holding"]
        sum_retention = raw_metrics["sum_retention"]
        active_vehs = raw_metrics.get("active_vehicles") or []
        plant_code = filters.get("plant_id") or "ALL"
        plant_display = plant_code if plant_code != "ALL" else "METROPOLITAN"

        # Deterministic High Priority Issue Count
        high_priority_cnt = holding_breaches + retention_breaches

        recommendations: list[RecommendationRowDTO] = []
        insights: list[DecisionInsightCardDTO] = []

        if dispatches > 0:
            avg_holding = sum_holding / max(1, dispatches)
            avg_retention = sum_retention / max(1, dispatches)

            # Rule 1: Critical Holding Queue Spillover (Holding > 20m)
            if holding_breaches > 0 or avg_holding > 20.0:
                v_target = active_vehs[0] if len(active_vehs) > 0 else "TM-001"
                conf = round(min(99.0, 85.0 + (avg_holding * 0.4)), 1)
                recommendations.append(
                    RecommendationRowDTO(
                        recommendation_id="REC-CRIT-01",
                        priority="CRITICAL",
                        recommendation_text=f"Re-route 2 idle mixer trucks to {plant_display} for peak unloading",
                        underlying_reason=f"Severe queue spillover ({holding_breaches} holding SLA breaches detected)",
                        affected_plant=plant_display,
                        affected_vehicle=v_target,
                        expected_impact="Queue -35%",
                        confidence_pct=conf,
                        status="Pending",
                    )
                )

            # Rule 2: High Dispatch Spacing Interval Delay (Avg Holding > 10m)
            if avg_holding > 10.0:
                v_target = active_vehs[1] if len(active_vehs) > 1 else (active_vehs[0] if len(active_vehs) > 0 else "TM-002")
                conf = round(min(98.0, 80.0 + (avg_holding * 0.5)), 1)
                recommendations.append(
                    RecommendationRowDTO(
                        recommendation_id="REC-HIGH-01",
                        priority="HIGH",
                        recommendation_text=f"Increase dispatch spacing between 10:00–12:00 by 8 mins for {plant_display}",
                        underlying_reason=f"Current site unloading capacity exceeded (avg holding {round(avg_holding, 1)}m)",
                        affected_plant=plant_display,
                        affected_vehicle=v_target,
                        expected_impact="Holding -18%",
                        confidence_pct=conf,
                        status="Pending",
                    )
                )

            # Rule 3: Medium Retention & Unloader Bottleneck (Retention Breaches > 0)
            if retention_breaches > 0 or avg_retention > 10.0:
                v_target = active_vehs[2] if len(active_vehs) > 2 else (active_vehs[0] if len(active_vehs) > 0 else "TM-003")
                conf = round(min(95.0, 75.0 + (avg_retention * 0.6)), 1)
                recommendations.append(
                    RecommendationRowDTO(
                        recommendation_id="REC-MED-01",
                        priority="MEDIUM",
                        recommendation_text=f"Prioritize unloading bay 2 for high-slump mix dispatches at {plant_display}",
                        underlying_reason=f"Unloader bottleneck causing site retention delay ({retention_breaches} breaches)",
                        affected_plant=plant_display,
                        affected_vehicle=v_target,
                        expected_impact="Retention -12%",
                        confidence_pct=conf,
                        status="Pending",
                    )
                )

            # Rule 4: Low Overlapping Customer Delivery Windows (Dispatches >= 5)
            if dispatches >= 5:
                v_target = active_vehs[3] if len(active_vehs) > 3 else (active_vehs[0] if len(active_vehs) > 0 else "TM-004")
                conf = 92.0
                recommendations.append(
                    RecommendationRowDTO(
                        recommendation_id="REC-LOW-01",
                        priority="LOW",
                        recommendation_text=f"Stagger afternoon dispatch departures starting 14:00 at {plant_display}",
                        underlying_reason="Overlapping customer site delivery windows across plant cluster",
                        affected_plant=plant_display,
                        affected_vehicle=v_target,
                        expected_impact="Overlap -22%",
                        confidence_pct=conf,
                        status="Pending",
                    )
                )

        # Sort Recommendations strictly by Priority Severity: CRITICAL -> HIGH -> MEDIUM -> LOW
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))

        # Dynamic Metrics Math
        active_rec_cnt = len(recommendations)
        
        if active_rec_cnt > 0:
            est_delay_reduction = round(sum_holding * 0.15, 1) if sum_holding > 0 else 0.0
            raw_sla = (high_priority_cnt / max(1, dispatches)) * 100.0
            sla_recovery = max(0.0, min(100.0, round(min(45.0, raw_sla), 1)))
            raw_fleet = (high_priority_cnt / max(1, len(active_vehs) or 1)) * 12.5
            fleet_opp = max(0.0, min(100.0, round(min(35.0, raw_fleet), 1)))
        else:
            est_delay_reduction = 0.0
            sla_recovery = 0.0
            fleet_opp = 0.0

        summary = DecisionSummaryDTO(
            active_recommendations=active_rec_cnt,
            high_priority_issues=high_priority_cnt,
            estimated_delay_reduction_mins=est_delay_reduction,
            estimated_sla_recovery_pct=sla_recovery,
            fleet_efficiency_opportunity_pct=fleet_opp,
        )

        # Dynamic Advisory Cards
        if any(r.priority == "CRITICAL" for r in recommendations):
            insights.append(
                DecisionInsightCardDTO(
                    title="Queue Bottleneck Spillover Prevention",
                    category="Queue Management",
                    action_type="Immediate Dispatch Spacing",
                    description=f"Active holding queue spillover at {plant_display}. Re-route TMs immediately.",
                    urgency="Immediate",
                )
            )

        if any(r.priority == "HIGH" for r in recommendations):
            insights.append(
                DecisionInsightCardDTO(
                    title="Fleet Asset Capacity Rebalancing",
                    category="Vehicle Redistribution",
                    action_type="Asset Re-allocation",
                    description=f"Move idle mixer trucks to {plant_display} to absorb peak customer unloading rates.",
                    urgency="Proactive",
                )
            )

        if not insights:
            insights.append(
                DecisionInsightCardDTO(
                    title="Operational Fleet Health Optimal",
                    category="System Compliance",
                    action_type="Monitoring Mode",
                    description="All dispatches operating within target holding and retention SLA thresholds.",
                    urgency="Proactive",
                )
            )

        return summary, recommendations, insights
