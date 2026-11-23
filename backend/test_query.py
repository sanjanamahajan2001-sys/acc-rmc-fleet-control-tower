import asyncio
import traceback
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService

async def test_endpoint():
    async with AsyncSessionFactory() as session:
        params = DashboardFilterParams(operation_date='2026-08-05', dataset_id='DS-20260805-01')
        try:
            res = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
            print('ENDPOINT SUCCESS! Snapshots returned:', len(res.snapshots))
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_endpoint())
