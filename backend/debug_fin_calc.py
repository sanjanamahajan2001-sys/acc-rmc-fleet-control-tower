import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.calculation_engine import FinancialCalculationEngine

async def debug_fin():
    async with AsyncSessionFactory() as session:
        res = await session.execute(select(MLPredictionSnapshot).limit(5))
        snaps = res.scalars().all()
        for s in snaps:
            try:
                metrics = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
                    session=session,
                    model_name=s.model_name,
                    predicted_value=s.predicted_value,
                    confidence_score=s.confidence_score,
                    plant_code=s.plant_code,
                    customer_code=s.customer_code,
                    input_features=s.input_features or {},
                    target_date=s.prediction_timestamp,
                )
                print(f"✅ SUCCESS for {s.model_name}: {metrics}")
            except Exception as e:
                import traceback
                print(f"❌ ERROR for {s.model_name}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_fin())
