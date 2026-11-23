"""
WS-10 Phase 6.2 Inference Safety Gate Service
Validates model prediction outputs against strict numerical, probabilistic, and multi-class boundaries.
Enforces NO CLAMPING policy: invalid outputs raise SafetyGateViolationError and reject snapshot persistence.
"""

import math
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

from app.modules.operational_intelligence.services.model_runtime_adapter import PredictionOutputDTO

logger = logging.getLogger(__name__)


class SafetyGateViolationError(ValueError):
    """Raised when a model prediction output violates numerical or category safety boundaries."""
    pass


class InferenceSafetyGateService:
    """
    Production Safety Gate Service for validating ML prediction outputs.
    Strictly enforces mathematical boundaries without clamping or altering raw values.
    """

    @classmethod
    def validate_prediction_output(cls, output: PredictionOutputDTO) -> None:
        """
        Validates PredictionOutputDTO against strict model-family safety rules.
        Raises SafetyGateViolationError if output is invalid.
        """
        val = output.prediction_value

        # 1. NaN and Infinity Checks
        if math.isnan(val) or math.isinf(val):
            logger.error(f"[SAFETY GATE] Invalid non-finite numeric value '{val}' for model {output.model_name}:{output.model_version}")
            raise SafetyGateViolationError(f"SAFETY_GATE_VIOLATION: Non-finite numeric prediction '{val}' for model {output.model_name}:{output.model_version}")

        # 2. Regression Safety Gate Rules
        if "regressor" in output.model_name:
            if val < 0.0:
                logger.error(f"[SAFETY GATE] Negative regression prediction '{val}' for model {output.model_name}:{output.model_version}")
                raise SafetyGateViolationError(f"SAFETY_GATE_VIOLATION: Negative regression output '{val}' is impossible for {output.model_name}")

        # 3. Binary Classification Rules (SLA Breach Classifier)
        elif output.model_name == "sla_breach_classifier":
            if not (0.0 <= val <= 1.0):
                logger.error(f"[SAFETY GATE] Probability '{val}' outside boundary [0, 1] for sla_breach_classifier")
                raise SafetyGateViolationError(f"SAFETY_GATE_VIOLATION: Probability '{val}' out of bounds [0.0, 1.0]")

        # 4. Multi-Class Plant Risk Classifier Rules
        elif output.model_name == "plant_risk_classifier":
            cls_val = output.multiclass_class
            if cls_val is None or cls_val not in {0, 1, 2}:
                logger.error(f"[SAFETY GATE] Invalid plant-risk class '{cls_val}' for plant_risk_classifier")
                raise SafetyGateViolationError(f"SAFETY_GATE_VIOLATION: Invalid plant-risk class '{cls_val}'. Must be 0 (NORMAL), 1 (MODERATE), or 2 (SEVERE)")

        logger.debug(f"[SAFETY GATE] Passed validation for {output.model_name}:{output.model_version} -> val={val}")
