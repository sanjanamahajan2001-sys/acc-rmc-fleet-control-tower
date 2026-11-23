import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot

async def check():
    async with AsyncSessionFactory() as session:
        res = await session.execute(select(MLPredictionSnapshot).limit(5))
        snaps = res.scalars().all()
        print("=== SNAPSHOT FINANCIAL EXPOSURE JSON ===")
        for s in snaps:
            print(f"ID: {s.prediction_snapshot_id}, Model: {s.model_name}")
            print(f"  Financial JSON: {s.financial_exposure_json}")

if __name__ == "__main__":
    asyncio.run(check())
