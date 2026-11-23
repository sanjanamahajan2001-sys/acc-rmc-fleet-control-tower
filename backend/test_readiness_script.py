import asyncio
import json
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine

async def run():
    async with AsyncSessionFactory() as session:
        res = await OptimizationReadinessEngine.evaluate_readiness(session, {
