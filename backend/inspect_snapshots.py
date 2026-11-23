import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.erp.models import Dispatch

async def check():
    async with AsyncSessionFactory() as session:
        snap_cnt = (await session.execute(select(func.count(MLPredictionSnapshot.id)))).scalar()
        disp_cnt = (await session.execute(select(func.count(Dispatch.id)))).scalar()
        print(f"Total MLPredictionSnapshots in DB: {snap_cnt}")
        print(f"Total Dispatches in DB: {disp_cnt}")

        disps = (await session.execute(select(Dispatch).limit(10))).scalars().all()
        for d in disps:
            print(f"DISP: id={d.id}, dispatch_number={d.dispatch_number}, plant_id={d.plant_id}")

if __name__ == "__main__":
    asyncio.run(check())
