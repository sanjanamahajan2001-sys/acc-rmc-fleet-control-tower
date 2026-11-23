"""
WS-10 Phase 4: ERP Field Dependency Graph Service.
Provides explicit mapping between ERP fields, FeatureSetV1 inputs, affected model families,
derived calculations, and downstream operational UI views.
"""

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


# Authoritative ERP Field to Predictive Feature & Model Dependency Matrix
ERP_FIELD_DEPENDENCY_MATRIX = {
    "plant_code": {
        "features_affected": ["plant_code"],
        "models_affected": [
            "delay_regressor",
            "turnaround_regressor",
            "sla_breach_classifier",
            "plant_risk_classifier",
        ],
        "calculations_affected": [
            "HOLDING_IDLE_RATE",
            "PLANT_CONGESTION_RISK",
            "financial_exposure_inr",
            "plant_congestion_risk_inr",
        ],
        "ui_affected": ["plant_risk_vector", "top_delayed_dispatches", "total_financial_risk"],
    },
    "customer_code": {
        "features_affected": ["customer_code"],
        "models_affected": [
            "sla_breach_classifier",
            "delay_regressor",
            "turnaround_regressor",
        ],
        "calculations_affected": [
            "CUSTOMER_RETENTION_RATE",
            "SLA_BREACH_PENALTY",
            "sla_penalty_risk_inr",
            "idle_queue_cost_inr",
        ],
        "ui_affected": ["high_sla_risk_dispatches", "customer_demurrage_vector"],
    },
    "vehicle_code": {
        "features_affected": ["vehicle_code"],
        "models_affected": ["delay_regressor", "turnaround_regressor"],
        "calculations_affected": ["financial_exposure_inr"],
        "ui_affected": ["vehicle_assignment_cards"],
    },
    "dispatch_time": {
        "features_affected": ["dispatch_hour", "dispatch_day_of_week"],
        "models_affected": [
            "delay_regressor",
            "turnaround_regressor",
            "sla_breach_classifier",
            "plant_risk_classifier",
        ],
        "calculations_affected": ["effective_rate_resolution_date"],
        "ui_affected": ["operational_timing_vector"],
    },
    "t2a_holding_mins": {
        "features_affected": ["plant_queue_avg_30d"],
        "models_affected": [
            "delay_regressor",
            "turnaround_regressor",
            "plant_risk_classifier",
        ],
        "calculations_affected": ["financial_exposure_inr", "idle_queue_cost_inr"],
        "ui_affected": ["queue_delay_cards", "plant_congestion_risk"],
    },
    "t2c_retention_mins": {
        "features_affected": ["customer_retention_avg_30d"],
        "models_affected": ["turnaround_regressor", "sla_breach_classifier"],
        "calculations_affected": ["idle_queue_cost_inr", "sla_penalty_risk_inr"],
        "ui_affected": ["retention_delay_cards"],
    },
    "ticket_volume_m3": {
        "features_affected": ["ticket_volume_m3"],
        "models_affected": ["turnaround_regressor", "delay_regressor"],
        "calculations_affected": ["financial_exposure_inr"],
        "ui_affected": ["volume_throughput_cards"],
    },
}


class ERPDependencyGraphService:
    """
    Manages explicit field-level dependency evaluation for targeted invalidation and recomputation.
    """

    @classmethod
    def evaluate_affected_models(cls, changed_fields: List[str]) -> Set[str]:
        """
        Given a list of modified ERP fields, returns the minimal set of model families
        that must be invalidated and recomputed.
        """
        affected_models: Set[str] = set()
        for field in changed_fields:
            if field in ERP_FIELD_DEPENDENCY_MATRIX:
                models = ERP_FIELD_DEPENDENCY_MATRIX[field]["models_affected"]
                affected_models.update(models)

        # If specific changed_fields were provided, return only affected models (or empty set if no ML features affected)
        return affected_models

    @classmethod
    def is_material_change(cls, old_features: Dict[str, Any], new_features: Dict[str, Any]) -> bool:
        """
        Evaluates whether a new feature set contains material business changes compared to the old feature set.
        If all relevant values are identical, returns False (preventing unnecessary prediction regeneration).
        """
        relevant_keys = [
            "plant_code",
            "customer_code",
            "vehicle_code",
            "dispatch_hour",
            "dispatch_day_of_week",
            "ticket_volume_m3",
            "plant_queue_avg_30d",
            "customer_retention_avg_30d",
        ]
        for key in relevant_keys:
            if old_features.get(key) != new_features.get(key):
                return True
        return False
