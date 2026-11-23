import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.timeline.service import TimelineService

@pytest.mark.asyncio
async def test_timeline_service_execution():
    async with AsyncSessionFactory() as session:
        timeline_dto = await TimelineService.compute_timeline(session, {"dataset_type": "ALL"})
        
        assert timeline_dto is not None
        assert timeline_dto.first_unloading_time != ""
        assert len(timeline_dto.tm_timelines) >= 0
