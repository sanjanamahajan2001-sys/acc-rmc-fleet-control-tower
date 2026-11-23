import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.tm_details.service import TMDetailsService

@pytest.mark.asyncio
async def test_tm_details_service_execution():
    async with AsyncSessionFactory() as session:
        response = await TMDetailsService.get_tm_details(session, {"dataset_type": "ALL"}, page=1, page_size=20)
        
        assert response is not None
        assert response.total_count >= 0
        assert response.page == 1
        assert response.page_size == 20
        assert isinstance(response.items, list)
