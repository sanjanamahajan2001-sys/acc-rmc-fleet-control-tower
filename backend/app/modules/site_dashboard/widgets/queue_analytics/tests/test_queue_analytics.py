import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.queue_analytics.service import QueueAnalyticsService

@pytest.mark.asyncio
async def test_queue_analytics_service_execution():
    async with AsyncSessionFactory() as session:
        response = await QueueAnalyticsService.compute_queue_analytics(session, {"dataset_type": "ALL"})
        
        assert response is not None
        assert response.queue is not None
        assert response.queue.avg_queue >= 0.0
        assert len(response.queue.points) >= 0
        assert len(response.root_causes) >= 0
