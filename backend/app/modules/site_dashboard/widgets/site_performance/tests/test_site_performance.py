import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.site_performance.service import SitePerformanceService

@pytest.mark.asyncio
async def test_site_performance_service_execution():
    async with AsyncSessionFactory() as session:
        response = await SitePerformanceService.get_site_performance(session, {"dataset_type": "ALL"})
        
        assert response is not None
        assert response.summary is not None
        assert response.summary.total_dispatches >= 0
        assert response.summary.compliance_pct >= 0.0
        assert isinstance(response.delay_distribution, list)
        assert isinstance(response.insights, list)
