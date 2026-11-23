"""
Standalone Production Calculation Rate Configuration Seeding Script
Seeds the 5 authoritative financial exposure rate rules into PostgreSQL table calculation_rate_configurations.
Enforces effective_from = 2020-01-01 to cover all historical and present prediction snapshot timestamps.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select, update
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.calculation_rate_config import CalculationRateConfiguration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_rate_configurations")

EFFECTIVE_START = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

DEFAULT_RATES = [
    {
        "rate_id": "RATE-GLOBAL-HOLDING-V1",
        "rate_code": "HOLDING_IDLE_RATE",
        "rate_value": Decimal("450.00"),
        "currency": "INR",
        "is_active": True,
        "description": "Standard truck holding idle cost per hour",
        "metadata_payload": {"description": "Standard truck holding idle cost per hour"},
    },
    {
        "rate_id": "RATE-GLOBAL-RETENTION-V1",
        "rate_code": "CUSTOMER_RETENTION_RATE",
        "rate_value": Decimal("650.00"),
        "currency": "INR",
        "is_active": True,
        "description": "Customer retention delay penalty per hour",
        "metadata_payload": {"description": "Customer retention delay penalty per hour"},
    },
    {
        "rate_id": "RATE-GLOBAL-SLA-PENALTY-V1",
        "rate_code": "SLA_BREACH_PENALTY",
        "rate_value": Decimal("2500.00"),
        "currency": "INR",
        "is_active": True,
        "description": "Flat penalty for customer delivery SLA breach",
        "metadata_payload": {"description": "Flat penalty for customer delivery SLA breach"},
    },
    {
        "rate_id": "RATE-GLOBAL-PLANT-RISK-V1",
        "rate_code": "PLANT_CONGESTION_RISK",
        "rate_value": Decimal("1500.00"),
        "currency": "INR",
        "is_active": True,
        "description": "Base financial risk penalty for plant congestion",
        "metadata_payload": {"description": "Base financial risk penalty for plant congestion"},
    },
    {
        "rate_id": "RATE-GLOBAL-BENCHMARK-V1",
        "rate_code": "STANDARD_TURNAROUND_BENCHMARK",
        "rate_value": Decimal("120.00"),
        "currency": "MINS",
        "is_active": True,
        "description": "Target standard trip turnaround time benchmark in minutes",
        "metadata_payload": {"description": "Target standard trip turnaround time benchmark in minutes"},
    },
]

async def seed_rate_configurations():
    async with AsyncSessionFactory() as session:
        seeded_count = 0
        for rate_data in DEFAULT_RATES:
            stmt = select(CalculationRateConfiguration).where(
                CalculationRateConfiguration.rate_id == rate_data["rate_id"]
            )
            res = await session.execute(stmt)
            existing = res.scalars().first()

            if not existing:
                config = CalculationRateConfiguration(
                    rate_id=rate_data["rate_id"],
                    rate_code=rate_data["rate_code"],
                    rate_value=rate_data["rate_value"],
                    currency=rate_data["currency"],
                    is_active=rate_data["is_active"],
                    description=rate_data["description"],
                    metadata_payload=rate_data["metadata_payload"],
                    effective_from=EFFECTIVE_START,
                )
                session.add(config)
                seeded_count += 1
                logger.info(f"SEEDED RATE CONFIG: {rate_data['rate_code']} = {rate_data['rate_value']} {rate_data['currency']}")
            else:
                existing.is_active = True
                existing.rate_value = rate_data["rate_value"]
                existing.description = rate_data["description"]
                existing.metadata_payload = rate_data["metadata_payload"]
                existing.effective_from = EFFECTIVE_START
                logger.info(f"UPDATED RATE CONFIG: {rate_data['rate_code']} = {rate_data['rate_value']} {rate_data['currency']} (Effective: {EFFECTIVE_START.isoformat()})")

        await session.commit()
        logger.info(f"=== CALCULATION RATE CONFIGURATION SEEDING COMPLETE (Seeded/Updated: {len(DEFAULT_RATES)}) ===")

if __name__ == "__main__":
    asyncio.run(seed_rate_configurations())
