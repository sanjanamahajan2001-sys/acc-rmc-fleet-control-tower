"""
WS-10 Phase 6.2 Safety Gates & Boundary Validation Test Suite
Validates strict non-clamping output safety gates for NaN, Inf, negative regression values,
out-of-bounds probabilities, and invalid plant risk classes.
"""

import math
import pytest
from app.modules.operational_intelligence.services.model_runtime_adapter import PredictionOutputDTO
from app.modules.operational_intelligence.services.inference_safety_gate_service import (
    InferenceSafetyGateService,
    SafetyGateViolationError,
)

def test_safety_gate_valid_regression():
    """Valid positive regression prediction passes validation."""
    out = PredictionOutputDTO(
        model_name="delay_regressor",
        model_version="v1.0.0",
        prediction_value=24.5,
        raw_output=24.5,
    )
    InferenceSafetyGateService.validate_prediction_output(out)


def test_safety_gate_negative_regression_rejection():
    """Negative regression prediction raises SafetyGateViolationError without clamping."""
    out = PredictionOutputDTO(
        model_name="delay_regressor",
        model_version="v1.0.0",
        prediction_value=-12.0, # IMPOSSIBLE NEGATIVE VALUE!
        raw_output=-12.0,
    )
    with pytest.raises(SafetyGateViolationError, match="Negative regression output"):
        InferenceSafetyGateService.validate_prediction_output(out)


def test_safety_gate_nan_rejection():
    """NaN prediction raises SafetyGateViolationError."""
    out = PredictionOutputDTO(
        model_name="turnaround_regressor",
        model_version="v1.0.0",
        prediction_value=float("nan"),
        raw_output=float("nan"),
    )
    with pytest.raises(SafetyGateViolationError, match="Non-finite numeric prediction"):
        InferenceSafetyGateService.validate_prediction_output(out)


def test_safety_gate_inf_rejection():
    """Infinity prediction raises SafetyGateViolationError."""
    out = PredictionOutputDTO(
        model_name="turnaround_regressor",
        model_version="v1.0.0",
        prediction_value=float("inf"),
        raw_output=float("inf"),
    )
    with pytest.raises(SafetyGateViolationError, match="Non-finite numeric prediction"):
        InferenceSafetyGateService.validate_prediction_output(out)


def test_safety_gate_probability_out_of_bounds_rejection():
    """Probability > 1.0 raises SafetyGateViolationError."""
    out = PredictionOutputDTO(
        model_name="sla_breach_classifier",
        model_version="v1.0.0",
        prediction_value=1.45, # OUT OF BOUNDS!
        raw_output=1.45,
    )
    with pytest.raises(SafetyGateViolationError, match="Probability '1.45' out of bounds"):
        InferenceSafetyGateService.validate_prediction_output(out)


def test_safety_gate_invalid_plant_risk_class_rejection():
    """Plant risk class outside {0, 1, 2} raises SafetyGateViolationError."""
    out = PredictionOutputDTO(
        model_name="plant_risk_classifier",
        model_version="v1.0.0",
        prediction_value=5.0,
        raw_output=5.0,
        multiclass_class=5, # INVALID CLASS!
    )
    with pytest.raises(SafetyGateViolationError, match="Invalid plant-risk class '5'"):
        InferenceSafetyGateService.validate_prediction_output(out)
