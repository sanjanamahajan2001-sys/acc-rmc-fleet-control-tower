import asyncio
from app.core.database import AsyncSessionFactory
from sqlalchemy import text

async def inspect_dispatches():
    async with AsyncSessionFactory() as session:
        res1 = await session.execute(text("SELECT plant_id, COUNT(*) FROM dispatches GROUP BY plant_id"))
        print("DISPATCHES GROUP BY PLANT_ID:", res1.fetchall())

        res2 = await session.execute(text("SELECT d.plant_id, p.name, p.code, COUNT(*) FROM dispatches d JOIN plants p ON d.plant_id = p.id GROUP BY d.plant_id, p.name, p.code"))
        print("DISPATCHES JOIN PLANTS:", res2.fetchall())

if __name__ == "__main__":
    asyncio.run(inspect_dispatches())
