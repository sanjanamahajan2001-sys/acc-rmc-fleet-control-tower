import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionFactory

async def main():
    async with AsyncSessionFactory() as session:
        # 1. Delete synthetic test customers & test plants
        res1 = await session.execute(text("DELETE FROM customers WHERE code LIKE 'CUST-CRASH%' OR code LIKE 'CUST-REST%' OR code LIKE 'CUST-T%' OR code LIKE 'TEST-%';"))
        res2 = await session.execute(text("UPDATE plants SET is_deleted = true WHERE code LIKE 'PLANT-%';"))
        print(f"Deleted synthetic test customers: {res1.rowcount}, test plants: {res2.rowcount}")

        # 2. Re-assign dispatches pointing to duplicate plant IDs to canonical plant ID
        plants = (await session.execute(text("SELECT id, code FROM plants ORDER BY created_at ASC;"))).fetchall()
        canonical_map = {}
        for pid, code in plants:
            if code not in canonical_map:
                canonical_map[code] = str(pid)
            else:
                # Point dispatches from duplicate pid to canonical_map[code]
                await session.execute(text(f"UPDATE dispatches SET plant_id = '{canonical_map[code]}' WHERE plant_id = '{pid}';"))
                await session.execute(text(f"DELETE FROM plants WHERE id = '{pid}';"))

        await session.commit()
        print("✅ Cleaned up synthetic test customers and deduplicated plant table!")

if __name__ == "__main__":
    asyncio.run(main())
