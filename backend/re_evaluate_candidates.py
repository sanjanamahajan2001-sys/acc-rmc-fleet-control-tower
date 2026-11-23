import asyncio
import json
from sqlalchemy import select
from app.core.database import AsyncSessionFactory, engine
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator

async def evaluate_candidates():
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        res = await session.execute(select(MLModelVersion))
        models = res.scalars().all()
        print(f"=== RE-EVALUATING {len(models)} REGISTERED CANDIDATES AGAINST PHASE 7.3 PROMOTION GATE ===\n")
        
        for m in models:
            print(f"Candidate Model Name: {m.model_name}")
            print(f"  Version:            {m.model_version}")
            print(f"  Category:           {m.model_category}")
            print(f"  Target:             {m.target_name}")
            print(f"  Artifact Path:      {m.artifact_path}")
            print(f"  Artifact SHA-256:   {m.artifact_sha256}")
            print(f"  Current Status:     {m.lifecycle_status}")
            print(f"  Current Decision:   {m.evaluation_decision}")
            print(f"  Rejection Reasons:  {m.rejection_reasons}")
            
            # Re-evaluate candidate against Phase 7.3 Evaluator
            preflight, meta = Phase73PromotionGateEvaluator.verify_candidate_preflight(m.model_name)
            report = await Phase73PromotionGateEvaluator.evaluate_candidate(session, m.model_name)
            print(f"  Gate Evaluator Output:")
            print(f"    Overall Gate Passed: {report.overall_gate_passed}")
            print(f"    Promotion Decision:  {report.promotion_decision}")
            print(f"    Gate Rejections:     {report.rejection_reasons}")
            print(f"----------------------------------------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(evaluate_candidates())
