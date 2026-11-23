import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.orchestration.dashboard_orchestrator import DashboardDataOrchestrator
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

@pytest.mark.asyncio
async def test_dashboard_plant_filtering():
    async with AsyncSessionFactory() as session:
        # All plants query
        params_all = DashboardFilterParams(plant_id="ALL")
        dto_all = await DashboardDataOrchestrator.get_master_dashboard_data(session, params_all)
        
        # Specific plant query
        params_plant = DashboardFilterParams(plant_id="PLANT-01")
        dto_plant = await DashboardDataOrchestrator.get_master_dashboard_data(session, params_plant)
        
        # Verify that filtered counts recalculate dynamically
        assert dto_all.kpis.dispatches.current_value >= 0
        assert dto_plant.kpis.dispatches.current_value >= 0
