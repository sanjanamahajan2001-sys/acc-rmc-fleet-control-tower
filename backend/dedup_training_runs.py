import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionFactory

async def deduplicate():
    async with AsyncSessionFactory() as session:
        # Delete duplicate MLTrainingRun records keeping only the earliest row per config_hash
        sql = """
        DELETE FROM ml_training_runs
        WHERE id::text NOT IN (
            SELECT MIN(id::text)
            FROM ml_training_runs
            GROUP BY model_family, config_hash
        );
        """
        await session.execute(text(sql))
        await session.commit()
        print("Deduplicated ml_training_runs table successfully.")

if __name__ == "__main__":
    asyncio.run(deduplicate())
