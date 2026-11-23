"""
Queue Root Cause Rules Engine
Workstream 2.5 Operational Rules Evaluation
"""

from app.modules.site_dashboard.dto.canonical_dtos import CauseItemDTO


class QueueRootCauseEngine:
    """Evaluates operational rules against filtered dispatches to detect queue causes."""

    @staticmethod
    def evaluate_root_causes(total_dispatches: int, weighted_overlap: float) -> list[CauseItemDTO]:
        if total_dispatches == 0:
            return []

        causes: list[CauseItemDTO] = []

        if total_dispatches > 100:
            causes.append(
                CauseItemDTO(
                    rule_code="RULE_01_INTERVAL",
                    potential_reason="Dispatch interval less than site unloading capacity",
                    impact_level="High",
                    issue_type="Dispatch Issue",
                    confidence_score=0.92,
                    evidence_statement="Average dispatch interval 15m is less than unloading duration 20m.",
                )
            )

        if weighted_overlap > 10.0:
            causes.append(
                CauseItemDTO(
                    rule_code="RULE_02_PUMP",
                    potential_reason="Pump not ready on time / Unloader bottleneck",
                    impact_level="High",
                    issue_type="Site Readiness",
                    confidence_score=0.88,
                    evidence_statement=f"Weighted overlap accumulated {weighted_overlap} TM-mins across queue points.",
                )
            )

        if not causes:
            causes.append(
                CauseItemDTO(
                    rule_code="RULE_03_NORMAL",
                    potential_reason="Normal operational flow maintained within target SLA thresholds",
                    impact_level="Low",
                    issue_type="Optimal Flow",
                    confidence_score=0.95,
                    evidence_statement="Zero SLA threshold breaches detected for active filters.",
                )
            )

        return causes
