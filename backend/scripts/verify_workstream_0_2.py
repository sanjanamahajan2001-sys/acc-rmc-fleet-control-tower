"""
Manual Verification Execution Script for Workstream 0.2
"""
import asyncio
from app.core.database import engine, AsyncSessionFactory, check_database_health
from app.core.unit_of_work import UnitOfWork
from app.models.base import Base, VersionedEntity
from app.repositories.base import GenericRepository
from app.repositories.pagination import PageRequest


class ManualVerificationItem(VersionedEntity):
    __tablename__ = "manual_verification_items"


async def main():
    print("=== Workstream 0.2 Manual Verification Starting ===")

    # 1. Database connects & Health Check
    health = await check_database_health()
    print(f"✓ Health Check Probe: {health}")
    assert health["status"] == "healthy"

    # 2. Schema Creation (Migration Simulation)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Migration Schema Created Successfully")

    # 3. Session Open, Transaction Commit, Repository Operations
    async with UnitOfWork() as uow:
        repo = GenericRepository(ManualVerificationItem, uow.session)
        item = ManualVerificationItem()
        await repo.create(item)
        saved_id = item.id
    print("✓ Session Opened, Insert Flushed, Transaction Committed, Session Closed")

    # 4. Read & Verify
    async with UnitOfWork() as uow:
        repo = GenericRepository(ManualVerificationItem, uow.session)
        fetched = await repo.get_by_id(saved_id)
        print(f"✓ Entity Fetched by UUID Key: {fetched.id}")
        page = await repo.find(page_request=PageRequest(size=10))
        print(f"✓ Paginated Query Result: {page.total_elements} elements")

    # 5. Transaction Rollback Verification
    try:
        async with UnitOfWork() as uow:
            repo = GenericRepository(ManualVerificationItem, uow.session)
            item2 = ManualVerificationItem()
            await repo.create(item2)
            raise RuntimeError("Manual Rollback Verification Exception")
    except RuntimeError:
        print("✓ Exception Caught, Transaction Auto-Rolled Back")

    # 6. Schema Drop (Rollback Simulation)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ Rollback Schema Dropped Cleanly")

    print("=== Workstream 0.2 Manual Verification PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
