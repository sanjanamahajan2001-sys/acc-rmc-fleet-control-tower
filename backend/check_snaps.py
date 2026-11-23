import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot

async def main():
    async with AsyncSessionFactory() as session:
        stmt = select(MLPredictionSnapshot.plant_code, func.count(MLPredictionSnapshot.id)).group_by(MLPredictionSnapshot.plant_code)
        res = await session.execute(stmt)
        print("Snapshots by plant_code:", res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
