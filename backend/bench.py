import time
import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

async def bench():
    async with AsyncSessionFactory() as session:
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
        latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
            latencies.append((time.perf_counter() - t0) * 1000)
        latencies.sort()
        avg = sum(latencies) / len(latencies)
        med = latencies[len(latencies)//2]
        p95 = latencies[int(len(latencies)*0.95)]
        p99 = latencies[int(len(latencies)*0.99)]
        print(f"BENCHMARK: avg={avg:.2f}ms, med={med:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")

if __name__ == "__main__":
    asyncio.run(bench())
