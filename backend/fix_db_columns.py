import asyncio
from sqlalchemy import text
from app.core.database import engine
from app.models.base import Base
import app.modules.erp.models
import app.modules.operational_intelligence.models

async def fix():
    async with engine.begin() as conn:
        print("Ensuring PostgreSQL tables exist for WS5.6 & WS5.7 (MLTrainingRun, MLFeedbackRecord, ContinuousLearningTrigger)...")
        await conn.run_sync(Base.metadata.create_all)
        print("WS5.6 & WS5.7 Tables created/verified successfully!")

if __name__ == "__main__":
    asyncio.run(fix())
