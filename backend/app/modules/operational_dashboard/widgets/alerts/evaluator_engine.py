"""
WS-07.3 Alert Rules Evaluation Engine.
Deterministic business-rule evaluation engine for WS-07.
"""
import hashlib
import json
from typing import List, Dict, Any, Optional
from app.modules.operational_dashboard.widgets.alerts.dtos import (
    OperationalAlertItemDTO,
    AlertSeverityEnum,
    AlertStatusEnum,
)

RULE_VERSION = "v1.0.0"

class AlertRulesEvaluatorEngine:
    """
    Deterministic rule evaluation engine for operational dispatches and readiness state.
    Calculates SHA-256 canonical fingerprints and generates Alert Candidate DTOs.
    """

    @staticmethod
    def generate_canonical_fingerprint(
        alert_type: str,
        plant_id: str,
        customer_id: str,
        dispatch_id: str,
        rule_version: str = RULE_VERSION,
    ) -> str:
        """
        Generates a 64-character SHA-256 hash using canonical JSON ordering:
        {"alert_type": alert_type, "customer_id": customer_id, "dispatch_id": dispatch_id, "plant_id": plant_id, "rule_version": rule_version}
        """
        canonical_dict = {
            "alert_type": alert_type,
            "customer_id": customer_id,
            "dispatch_id": str(dispatch_id),
            "plant_id": plant_id,
            "rule_version": rule_version,
        }
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def evaluate_dispatches(
        cls,
        dispatches: List[Dict[str, Any]],
        dataset_id: str = "DS-ACTIVE-001",
        import_job_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates a list of scoped dispatches against Rules 1, 2, and 3.
        Returns candidate dicts ready for OperationalAlertModel persistence.
        """
        candidates: List[Dict[str, Any]] = []

        # Sort dispatches deterministically before evaluation
        sorted_dispatches = sorted(
            dispatches,
            key=lambda d: (
                dataset_id,
                d.get("plant_code") or d.get("plant_id") or "ALL",
                d.get("customer_code") or d.get("customer_id") or "ALL",
                str(d.get("dispatch_id", "")),
            )
        )

        for d in sorted_dispatches:
            # Exclude synthetic/generated data (REAL_ONLY enforcement)
            if d.get("is_generated") is True:
                continue

            dispatch_id = str(d.get("dispatch_id")) if d.get("dispatch_id") else None
            # Structured error / non-evaluable handling: Skip missing identifiers
            if not dispatch_id or dispatch_id == "None" or dispatch_id.strip() == "":
                continue

            plant_id = d.get("plant_code") or d.get("plant_id") or "ALL"
            customer_id = d.get("customer_code") or d.get("customer_id") or "ALL"
            vehicle_id = d.get("vehicle_id")

            # --- RULE 1: PLANT_HOLDING_BOTTLENECK ---
            t2a_holding = d.get("t2a_holding_mins")
            if t2a_holding is not None and float(t2a_holding) > 20.0:
                actual = float(t2a_holding)
                threshold = 20.0
                alert_type = "PLANT_HOLDING_BOTTLENECK"
                fp = cls.generate_canonical_fingerprint(alert_type, plant_id, customer_id, dispatch_id)

                candidates.append({
                    "alert_fingerprint": fp,
                    "alert_type": alert_type,
                    "severity": "CRITICAL",
                    "status": "OPEN",
                    "plant_id": plant_id,
                    "customer_id": customer_id,
                    "dispatch_id": dispatch_id,
                    "vehicle_id": vehicle_id,
                    "dataset_id": dataset_id,
                    "import_job_id": import_job_id,
                    "metric_name": "t2a_holding_mins",
                    "actual_value": actual,
                    "threshold_value": threshold,
                    "unit": "mins",
                    "business_impact": "Plant departure queue bottleneck",
                    "evidence_json": {
                        "actual": actual,
                        "threshold": threshold,
                        "exceeded_mins": round(actual - threshold, 2),
                        "dispatch_id": dispatch_id,
                        "plant_id": plant_id,
                        "customer_id": customer_id,
                    },
                    "recommended_action": "Pace plant departure cadence to clear queue bottleneck.",
                    "rule_version": RULE_VERSION,
                })

            # --- RULE 2: SITE_RETENTION_EXCESSIVE ---
            t2c_retention = d.get("t2c_retention_mins")
            if t2c_retention is not None and float(t2c_retention) > 20.0:
                actual = float(t2c_retention)
                threshold = 20.0
                alert_type = "SITE_RETENTION_EXCESSIVE"
                fp = cls.generate_canonical_fingerprint(alert_type, plant_id, customer_id, dispatch_id)

                candidates.append({
                    "alert_fingerprint": fp,
                    "alert_type": alert_type,
                    "severity": "WARNING",
                    "status": "OPEN",
                    "plant_id": plant_id,
                    "customer_id": customer_id,
                    "dispatch_id": dispatch_id,
                    "vehicle_id": vehicle_id,
                    "dataset_id": dataset_id,
                    "import_job_id": import_job_id,
                    "metric_name": "t2c_retention_mins",
                    "actual_value": actual,
                    "threshold_value": threshold,
                    "unit": "mins",
                    "business_impact": "Customer site unloading detention delay",
                    "evidence_json": {
                        "actual": actual,
                        "threshold": threshold,
                        "exceeded_mins": round(actual - threshold, 2),
                        "dispatch_id": dispatch_id,
                        "plant_id": plant_id,
                        "customer_id": customer_id,
                    },
                    "recommended_action": "Review customer site unloading constraints with site supervisor.",
                    "rule_version": RULE_VERSION,
                })

            # --- RULE 3: TRANSIT_DELAY_EXCESSIVE ---
            t1_transit = d.get("t1_transit_mins")
            if t1_transit is not None and float(t1_transit) > 60.0:
                actual = float(t1_transit)
                threshold = 60.0
                alert_type = "TRANSIT_DELAY_EXCESSIVE"
                fp = cls.generate_canonical_fingerprint(alert_type, plant_id, customer_id, dispatch_id)

                candidates.append({
                    "alert_fingerprint": fp,
                    "alert_type": alert_type,
                    "severity": "WARNING",
                    "status": "OPEN",
                    "plant_id": plant_id,
                    "customer_id": customer_id,
                    "dispatch_id": dispatch_id,
                    "vehicle_id": vehicle_id,
                    "dataset_id": dataset_id,
                    "import_job_id": import_job_id,
                    "metric_name": "t1_transit_mins",
                    "actual_value": actual,
                    "threshold_value": threshold,
                    "unit": "mins",
                    "business_impact": "Excessive transit duration delay",
                    "evidence_json": {
                        "actual": actual,
                        "threshold": threshold,
                        "exceeded_mins": round(actual - threshold, 2),
                        "dispatch_id": dispatch_id,
                        "plant_id": plant_id,
                        "customer_id": customer_id,
                    },
                    "recommended_action": "Inspect route transit logs for vehicle traffic congestion.",
                    "rule_version": RULE_VERSION,
                })

        # Deterministic sorting of candidates before returning
        candidates.sort(key=lambda x: (
            x["dataset_id"],
            x["plant_id"],
            x["customer_id"],
            x["dispatch_id"],
            x["alert_type"],
        ))

        return candidates

    @classmethod
    def evaluate_readiness(
        cls,
        readiness_status: str,
        quality_summary: Dict[str, Any],
        blocking_conditions: List[str],
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: str = "DS-ACTIVE-001",
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates Rule 4: DEGRADED_DATA_QUALITY based on OptimizationReadinessEngine status.
        Produces ONE single deterministic readiness candidate for the dataset scope when DEGRADED.
        """
        if not readiness_status or readiness_status.upper() != "DEGRADED":
            return None

        alert_type = "DEGRADED_DATA_QUALITY"
        # Deterministic UUID placeholder for readiness dataset scope
        scope_dispatch_id = "00000000-0000-0000-0000-000000000000"
        fp = cls.generate_canonical_fingerprint(alert_type, plant_id, customer_id, scope_dispatch_id)

        return {
            "alert_fingerprint": fp,
            "alert_type": alert_type,
            "severity": "INFO",
            "status": "OPEN",
            "plant_id": plant_id,
            "customer_id": customer_id,
            "dispatch_id": None,
            "vehicle_id": None,
            "dataset_id": dataset_id,
            "import_job_id": None,
            "metric_name": "readiness_status",
            "actual_value": 0.0,
            "threshold_value": 0.0,
            "unit": "status",
            "business_impact": "Degraded dataset quality affects optimization readiness",
            "evidence_json": {
                "readiness_status": readiness_status,
                "quality_summary": quality_summary,
                "blocking_conditions": blocking_conditions,
                "plant_id": plant_id,
                "customer_id": customer_id,
            },
            "recommended_action": "Audit source ERP workbook mapping for missing timestamps or unmapped entities.",
            "rule_version": RULE_VERSION,
        }


# Backwards compatibility alias
AlertEvaluatorEngine = AlertRulesEvaluatorEngine
