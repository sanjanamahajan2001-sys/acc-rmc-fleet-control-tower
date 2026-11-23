import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot

async def check():
    async with AsyncSessionFactory() as session:
        r1 = await session.execute(select(func.count()).select_from(MLPredictionSnapshot))
        print("=== LOCALHOST DB SNAPSHOT VERIFICATION ===")
        print("TOTAL SNAPSHOTS IN DB:", r1.scalar())

        r2 = await session.execute(
            select(MLPredictionSnapshot.plant_code, func.count())
            .group_by(MLPredictionSnapshot.plant_code)
        )
        print("SNAPSHOT COUNT BY PLANT:", r2.all())

if __name__ == "__main__":
    asyncio.run(check())
