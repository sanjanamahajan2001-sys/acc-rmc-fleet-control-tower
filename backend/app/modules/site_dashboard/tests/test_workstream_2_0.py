import pytest
from app.modules.site_dashboard.dto.canonical_dtos import (
    DashboardKPIDTO,
    KPIItemDTO,
    DashboardSummaryDTO,
    MasterDashboardResponseDTO,
)
from app.modules.site_dashboard.cache.materialized_cache import (
    MaterializedDashboardCache,
    generate_filter_hash,
)

def test_canonical_dto_immutability():
    kpi = KPIItemDTO(
        key="holding",
        label="Holding Beyond 20 min",
        current_value=9.9,
        unit="hrs",
        status="WARNING",
    )
    assert kpi.key == "holding"
    assert kpi.current_value == 9.9

    # Verify immutability
    with pytest.raises(Exception):
        kpi.current_value = 12.0  # type: ignore

def test_cache_hashing_and_invalidation():
    filters1 = {"plant_id": "P01", "date_from": "2026-08-01"}
    filters2 = {"date_from": "2026-08-01", "plant_id": "P01"}
    
    hash1 = generate_filter_hash(filters1)
    hash2 = generate_filter_hash(filters2)
    assert hash1 == hash2  # Deterministic hashing regardless of key order

    MaterializedDashboardCache.invalidate_all()
    assert MaterializedDashboardCache.get(filters1) is None
