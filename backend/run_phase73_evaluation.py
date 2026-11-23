import asyncio
import json
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator

async def main():
    async with AsyncSessionFactory() as session:
        print("Executing Phase 7.3 Model Evaluation & Promotion Gate Suite...")
        res = await Phase73PromotionGateEvaluator.run_full_promotion_suite(session, dataset_id="DS-20260805-001")
        print(f"Timestamp: {res.evaluation_timestamp}")
        print(f"Evaluated Count: {res.models_evaluated_count}")
        print(f"Promoted Count: {res.promoted_models_count}")
        print(f"Platform Prediction Status: {res.platform_prediction_status}")
        print("\n--- MODEL EVALUATION MATRIX ---")
        for m_name, report in res.evaluations.items():
            print(f"\nModel: {m_name}")
            print(f"  Category: {report.category}")
            print(f"  Target: {report.target_name}")
            print(f"  Preflight Passed: {report.preflight.preflight_passed}")
            print(f"  SHA-256: {report.preflight.sha256_hash}")
            print(f"  Holdout Metrics: {report.metrics_holdout.model_dump_json()}")
            print(f"  Overall Gate Passed: {report.overall_gate_passed}")
            print(f"  Promotion Decision: {report.promotion_decision}")
            if report.rejection_reasons:
                print(f"  Rejection Reasons: {report.rejection_reasons}")

if __name__ == "__main__":
    asyncio.run(main())
