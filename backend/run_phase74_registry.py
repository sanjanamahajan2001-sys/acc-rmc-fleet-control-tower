import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.ml.trainer import Phase72ModelTrainer
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository

async def main():
    async with AsyncSessionFactory() as session:
        print("Executing Phase 7.4 Model Registry Persistence & Governance Verification...")
        repo = MLModelRegistryRepository(session)
        
        # 1. Train candidates to make sure artifacts are fresh
        print("Ensuring Phase 7.2 candidate artifacts are fresh...")
        await Phase72ModelTrainer.train_all_candidate_models(session, dataset_id="DS-20260805-001")

        # 2. Evaluate candidate models
        print("Running Phase 7.3 promotion gate evaluation...")
        suite_res = await Phase73PromotionGateEvaluator.run_full_promotion_suite(session, dataset_id="DS-20260805-001")

        # 3. Register and record evaluation results into PostgreSQL ml_model_versions table
        print("Registering candidate versions into PostgreSQL ml_model_versions table...")
        for m_name, report in suite_res.evaluations.items():
            preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight(m_name)
            
            # Register version
            v_entity = await repo.register_candidate_version(
                model_name=meta.model_name,
                model_category=meta.model_category,
                model_version=f"{meta.candidate_model_version}-reg",
                algorithm=meta.algorithm,
                target_name=meta.target_name,
                feature_set_version=meta.feature_set_version,
                training_dataset_id=meta.dataset_id,
                artifact_path=meta.artifact_path,
                artifact_sha256=meta.artifact_sha256,
                artifact_size_bytes=meta.artifact_size_bytes,
                training_timestamp=meta.training_timestamp,
                hyperparameters=meta.hyperparameters,
                random_seed=meta.random_seed,
                row_counts=meta.row_counts,
            )

            # Record Evaluation
            eval_entity = await repo.record_evaluation_result(m_name, f"{meta.candidate_model_version}-reg", report)
            print(f"Registered & Evaluated: {m_name} -> Status: {eval_entity.lifecycle_status}, Decision: {eval_entity.evaluation_decision}")

        # 4. Check active promoted models
        print("\n--- ACTIVE PROMOTED MODEL RESOLUTION CHECK ---")
        for m_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            active = await repo.get_active_promoted_model(m_name)
            status_str = active.model_version if active else "NOT_CONFIGURED"
            print(f"Model Family '{m_name}' Active Promoted Version: {status_str}")

        await session.commit()
        print("\nPhase 7.4 Registry Persistence Completed Successfully.")

if __name__ == "__main__":
    asyncio.run(main())
