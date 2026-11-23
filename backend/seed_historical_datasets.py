"""
Standalone Historical Dataset Seeding Script for WS5.5.
Populates READY_FOR_TRAINING datasets for delay_regressor, turnaround_regressor,
sla_breach_classifier, and plant_risk_classifier across historical dispatches.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.training_dataset_service import TrainingDatasetService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_historical_datasets")

async def main():
    families = [
        "delay_regressor",
        "turnaround_regressor",
        "sla_breach_classifier",
        "plant_risk_classifier",
    ]

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=365)
    end_time = now + timedelta(days=1)

    async with AsyncSessionFactory() as session:
        service = TrainingDatasetService(session)
        for family in families:
            try:
                ds = await service.generate_and_persist_dataset(
                    model_family=family,
                    source_time_range_start=start_time,
                    source_time_range_end=end_time,
                    evaluation_cutoff=end_time,
                    min_sample_count=1,
                )
                logger.info(f"DATASET CREATED: {family} -> {ds.dataset_id} (Rows: {ds.total_row_count}, Status: {ds.dataset_status})")
            except Exception as e:
                logger.warning(f"Dataset build for {family} failed/skipped: {e}")

    logger.info("=== HISTORICAL DATASET SEEDING COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
