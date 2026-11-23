import asyncio
import json
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer

async def main():
    async with AsyncSessionFactory() as session:
        print("Starting Phase 7.2 candidate model training...")
        results = await Phase72ModelTrainer.train_all_candidate_models(session, dataset_id="DS-20260805-001")
        for m_name, res in results.items():
            print(f"Model: {m_name}")
            print(f"  Artifact Path: {res.metadata.artifact_path}")
            print(f"  SHA-256: {res.metadata.artifact_sha256}")
            print(f"  Status: {res.metadata.promotion_status}")
            print(f"  Holdout Metrics: {res.metadata.metrics_holdout.model_dump_json()}")
            print(f"  Gate Assessment: {res.metadata.gate_assessment}")

if __name__ == "__main__":
    asyncio.run(main())
