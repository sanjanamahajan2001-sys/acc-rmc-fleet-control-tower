import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.active_inference_service import WS10ActiveModelInferenceService

async def test_batch():
    async with AsyncSessionFactory() as session:
        res = await WS10ActiveModelInferenceService.execute_batch_inference_for_new_dispatches(session)
        print("BATCH INFERENCE SUCCESS! Snapshots created:", res.get("snapshots_created"))

if __name__ == "__main__":
    asyncio.run(test_batch())
