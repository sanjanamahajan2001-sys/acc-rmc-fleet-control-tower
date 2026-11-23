"""
Standalone Candidate Model Generation Script for WS5.6.
Trains and registers candidate models for delay_regressor, turnaround_regressor,
sla_breach_classifier, and plant_risk_classifier.
"""

import asyncio
import logging
import uuid
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.model_training_service import ModelTrainingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_candidate_models")

async def main():
    families = [
        "delay_regressor",
        "turnaround_regressor",
        "sla_breach_classifier",
        "plant_risk_classifier",
    ]

    async with AsyncSessionFactory() as session:
        service = ModelTrainingService(session)
        for idx, family in enumerate(families):
            try:
                # Use distinct seed / version for production candidate generation
                res = await service.train_candidate_model(
                    model_family=family,
                    random_seed=100 + idx,
                    override_candidate_version=f"v1.1.0-cand-{family}",
                )
                logger.info(f"CANDIDATE MODEL REGISTERED: {family} -> {res.get('candidate_version')}")
            except Exception as e:
                logger.warning(f"Candidate model generation for {family} failed: {e}")

    logger.info("=== CANDIDATE MODEL GENERATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
