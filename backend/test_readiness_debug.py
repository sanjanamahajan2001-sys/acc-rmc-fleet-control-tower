import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine

async def run():
    async with AsyncSessionFactory() as session:
        res1 = await OptimizationReadinessEngine.evaluate_readiness(session, {"plant_id": None, "customer_id": None, "dataset_type": "ALL"})
        print("CASE 1 (None, None, ALL):", res1.status.value, res1.quality_summary.total_dispatches)

        res2 = await OptimizationReadinessEngine.evaluate_readiness(session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "ALL"})
        print("CASE 2 (ALL, ALL, ALL):", res2.status.value, res2.quality_summary.total_dispatches)

        res3 = await OptimizationReadinessEngine.evaluate_readiness(session, {"plant_id": None, "customer_id": None, "dataset_type": "REAL_ONLY"})
        print("CASE 3 (None, None, REAL_ONLY):", res3.status.value, res3.quality_summary.total_dispatches)

if __name__ == "__main__":
    asyncio.run(run())
