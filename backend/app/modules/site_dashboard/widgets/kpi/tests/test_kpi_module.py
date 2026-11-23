import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.kpi.service import KPIService

@pytest.mark.asyncio
async def test_kpi_service_execution():
    async with AsyncSessionFactory() as session:
        kpi_dto = await KPIService.compute_kpis(session, {"dataset_type": "ALL"})
        
        assert kpi_dto is not None
        assert kpi_dto.dispatches.key == "dispatches"
        assert kpi_dto.holding.status in ["OPTIMAL", "WARNING", "CRITICAL"]
        assert kpi_dto.accuracy.target == 90.0
