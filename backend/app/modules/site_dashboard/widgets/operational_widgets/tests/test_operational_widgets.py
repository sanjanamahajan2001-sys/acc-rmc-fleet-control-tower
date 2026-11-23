import pytest
import time
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.operational_widgets.service import OperationalWidgetsService
from app.modules.site_dashboard.widgets.operational_widgets.calculations import OperationalWidgetsCalculations


@pytest.mark.asyncio
async def test_operational_widgets_service_execution():
    async with AsyncSessionFactory() as session:
        t0 = time.perf_counter()
        response = await OperationalWidgetsService.get_operational_widgets(session, {"dataset_type": "ALL"})
        t1 = time.perf_counter()
        dur_ms = (t1 - t0) * 1000.0
        
        assert response is not None
        assert response.dashboard_health is not None
        assert response.dashboard_health.dashboard_status in ["GOOD", "WARNING", "CRITICAL"]
        assert response.dashboard_health.last_erp_import.endswith("18:30 IST")
        assert response.dashboard_health.canonical_snapshot_version.startswith("v2.10-SNAP-")
        assert len(response.readiness) == 8
        assert len(response.highlights) == 6
        assert isinstance(response.events, list)
        assert len(response.data_quality) == 4
        assert dur_ms < 300.0, f"Backend processing duration {dur_ms}ms exceeds 300ms SLA"

        # Verify empty state / non-matching filter response handling
        response_empty = await OperationalWidgetsService.get_operational_widgets(
            session,
            {"plant_id": "ACC_DHARGA", "customer_id": "CUST_NON_EXISTENT_999"}
        )
        assert response_empty.dashboard_health.total_records_evaluated == 0
        assert response_empty.dashboard_health.dashboard_status == "CRITICAL"
        assert response_empty.dashboard_health.import_completeness_pct == 0.0
        assert len(response_empty.events) == 0


def test_dashboard_health_status_transitions():
    """Validates status transitions: <2h GOOD, >6h/0 records CRITICAL/WARNING."""
    good_db = {"total_records": 500, "latest_date": "2025-08-15"}
    health_good = OperationalWidgetsCalculations.build_dashboard_health(good_db, 15.0, 15.0)
    assert health_good.dashboard_status == "GOOD"
    assert health_good.last_erp_import == "2025-08-15 18:30 IST"
    assert health_good.canonical_snapshot_version == "v2.10-SNAP-20250815"

    empty_db = {"total_records": 0, "latest_date": None}
    health_crit = OperationalWidgetsCalculations.build_dashboard_health(empty_db, 5.0, 5.0)
    assert health_crit.dashboard_status == "CRITICAL"
    assert health_crit.canonical_sync_status == "LAGGING"
