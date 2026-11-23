"""
KPI Business Logic & Threshold Evaluator
Workstream 2.2 Business Calculations
"""

from app.modules.site_dashboard.shared.duration_math import evaluate_threshold_status


class KPICalculations:
    """Calculates status, variance, and thresholds for KPI metrics."""

    @staticmethod
    def calculate_status(value: float, threshold: float, is_lower_better: bool = True) -> str:
        return evaluate_threshold_status(value, threshold, is_lower_better)

    @staticmethod
    def calculate_variance(value: float, target: float) -> float:
        if not target:
            return 0.0
        return round(value - target, 1)
