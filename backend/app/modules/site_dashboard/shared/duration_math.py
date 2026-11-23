"""
Shared Calculation Utilities for Dashboard Engine
Workstream 2.0 Shared Math
"""

import datetime
from typing import Any


def calculate_duration_minutes(start_dt: datetime.datetime | str, end_dt: datetime.datetime | str) -> float:
    """Calculates minutes between start and end timestamps."""
    if not start_dt or not end_dt:
        return 0.0
    if isinstance(start_dt, str):
        start_dt = datetime.datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
    if isinstance(end_dt, str):
        end_dt = datetime.datetime.fromisoformat(end_dt.replace("Z", "+00:00"))

    delta = (end_dt - start_dt).total_seconds() / 60.0
    return max(0.0, round(delta, 1))


def evaluate_threshold_status(value: float, threshold: float, is_lower_better: bool = True) -> str:
    """Evaluates threshold status (OPTIMAL, WARNING, CRITICAL)."""
    if is_lower_better:
        if value <= threshold:
            return "OPTIMAL"
        elif value <= threshold * 1.25:
            return "WARNING"
        return "CRITICAL"
    else:
        if value >= threshold:
            return "OPTIMAL"
        elif value >= threshold * 0.8:
            return "WARNING"
        return "CRITICAL"
