import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.calculation_rate_config import CalculationRateConfiguration

async def verify():
    async with AsyncSessionFactory() as session:
        cnt = (await session.execute(select(func.count(CalculationRateConfiguration.id)))).scalar() or 0
        print(f"==================================================")
        print(f"CALCULATION RATE CONFIGURATIONS IN DB: {cnt}")
        print(f"==================================================")
        if cnt == 0:
            print("❌ STATUS: EMPTY! (Need to run seed_rate_configurations.py)")
        else:
            print("✅ STATUS: OK! Rates exist in DB.")

if __name__ == "__main__":
    asyncio.run(verify())
