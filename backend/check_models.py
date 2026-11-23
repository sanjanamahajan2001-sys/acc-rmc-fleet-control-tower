import asyncio
from app.core.database import AsyncSessionFactory
from sqlalchemy import select
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion

async def check():
    async with AsyncSessionFactory() as session:
        res = await session.execute(select(MLModelVersion))
        models = res.scalars().all()
        print('FOUND MODELS IN DB:', len(models))
        for m in models:
            print(f'- {m.model_name} | version={m.model_version} | status={m.lifecycle_status} | id={m.id}')

asyncio.run(check())
