import asyncio
import os
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.calculation_rate_config import CalculationRateConfiguration

async def check():
    async with AsyncSessionFactory() as session:
        res = await session.execute(select(CalculationRateConfiguration))
        configs = res.scalars().all()
        print("=== LOCALHOST RATE CONFIGS ===")
        for c in configs:
            print(f"rate_id: {c.rate_id}, rate_code: {c.rate_code}, rate_value: {c.rate_value}")

if __name__ == "__main__":
    asyncio.run(check())
