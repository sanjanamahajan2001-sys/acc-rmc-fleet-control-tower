"""
Materialized In-Memory Dashboard Cache Store
Workstream 2.0 Materialized Cache
"""

import hashlib
import json
from typing import Any, Optional
from app.modules.site_dashboard.dto.canonical_dtos import MasterDashboardResponseDTO

_CACHE_STORE: dict[str, MasterDashboardResponseDTO] = {}


def generate_filter_hash(filters: dict[str, Any]) -> str:
    """Generates SHA-256 hash string for a filter parameter dictionary."""
    normalized_json = json.dumps(filters, sort_keys=True)
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


class MaterializedDashboardCache:
    """In-Memory Materialized Cache for Dashboard DTO Payloads."""

    @staticmethod
    def get(filters: dict[str, Any]) -> Optional[MasterDashboardResponseDTO]:
        key = generate_filter_hash(filters)
        return _CACHE_STORE.get(key)

    @staticmethod
    def set(filters: dict[str, Any], payload: MasterDashboardResponseDTO) -> None:
        key = generate_filter_hash(filters)
        _CACHE_STORE[key] = payload

    @staticmethod
    def invalidate_all() -> None:
        _CACHE_STORE.clear()
