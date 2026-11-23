"""
Dashboard Filter Engine
Workstream 2.1 Filter Normalization
"""

import datetime
from typing import Any
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams


class FilterEngine:
    """Filter Normalization, Validation, and Defaulting Engine."""

    @staticmethod
    def normalize_filters(params: DashboardFilterParams) -> dict[str, Any]:
        filters: dict[str, Any] = {
            "dataset_type": params.dataset_type or "ALL"
        }

        if params.date_from:
            filters["date_from"] = params.date_from
        else:
            filters["date_from"] = datetime.date.today().isoformat()

        if params.date_to:
            filters["date_to"] = params.date_to
        else:
            filters["date_to"] = datetime.date.today().isoformat()

        if params.plant_id:
            filters["plant_id"] = params.plant_id

        if params.customer_id:
            filters["customer_id"] = params.customer_id

        return filters
