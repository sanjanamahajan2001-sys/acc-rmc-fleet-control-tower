import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService

async def main():
    async with AsyncSessionFactory() as session:
        params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date="2026-08-05")
        ops_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
        print("Model dump keys:")
        for k, v in ops_overview.model_dump().items():
            print(f"  - {k}: {type(v)}")

if __name__ == "__main__":
    asyncio.run(main())
