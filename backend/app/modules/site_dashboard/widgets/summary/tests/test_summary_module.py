import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.summary.service import SummaryService

@pytest.mark.asyncio
async def test_summary_service_execution():
    async with AsyncSessionFactory() as session:
        summary_dto = await SummaryService.compute_summary(session, {"dataset_type": "ALL"})
        
        assert summary_dto is not None
        assert summary_dto.total_quantity_m3 >= 0.0
        assert summary_dto.avg_holding_mins >= 0.0
        assert len(summary_dto.top_sites_holding) >= 0
        assert len(summary_dto.top_sites_retention) >= 0
