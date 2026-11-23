import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.calculation_rate_config import CalculationRateConfiguration
from app.modules.operational_intelligence.services.calculation_engine import FinancialCalculationEngine

async def test_resolve():
    async with AsyncSessionFactory() as session:
        rate_codes = ["HOLDING_IDLE_RATE", "CUSTOMER_RETENTION_RATE", "SLA_BREACH_PENALTY", "PLANT_CONGESTION_RISK", "STANDARD_TURNAROUND_BENCHMARK"]
        for code in rate_codes:
            try:
                rate = await FinancialCalculationEngine.resolve_authoritative_rate(session, code)
                print(f"✅ RESOLVED {code}: {rate.rate_value}")
            except Exception as e:
                print(f"❌ FAILED {code}: {e}")

if __name__ == "__main__":
    asyncio.run(test_resolve())
