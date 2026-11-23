import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.erp.models import ImportJob, Dispatch

async def main():
    async with AsyncSessionFactory() as session:
        active_cnt = (await session.execute(select(Dispatch))).scalars().all()
        print(f'Active dispatches: {len(active_cnt)}')
        
        jobs = (await session.execute(select(ImportJob))).scalars().all()
        print(f'Total jobs: {len(jobs)}')
        
        # If active dispatches is 0, then all current jobs were before the reset
        if len(active_cnt) == 0:
            now_iso = datetime.now(timezone.utc).isoformat()
            for j in jobs:
                lineage = dict(j.source_lineage or {})
                lineage['is_reset'] = True
                lineage['reset_at'] = now_iso
                lineage['reset_by'] = 'admin'
                j.source_lineage = lineage
            await session.commit()
            print('Successfully marked all pre-reset jobs as reset=True')
        else:
            print('Active dispatches exist, skipping auto-marking')

if __name__ == '__main__':
    asyncio.run(main())
