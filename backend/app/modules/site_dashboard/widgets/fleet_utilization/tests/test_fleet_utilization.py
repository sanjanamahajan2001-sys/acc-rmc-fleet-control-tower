import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.fleet_utilization.service import FleetUtilizationService

@pytest.mark.asyncio
async def test_fleet_utilization_service_execution():
    async with AsyncSessionFactory() as session:
        response = await FleetUtilizationService.get_fleet_utilization(session, {"dataset_type": "ALL"})
        
        assert response is not None
        assert response.summary is not None
        assert response.summary.total_active_vehicles >= 0
        assert response.summary.fleet_utilization_pct >= 0.0
        assert isinstance(response.top_vehicles, list)
        assert isinstance(response.alerts, list)
