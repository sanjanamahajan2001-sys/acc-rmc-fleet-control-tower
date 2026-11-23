import asyncio
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, Ticket, Order, Driver, Site
from app.modules.operational_intelligence.tests.conftest import TestAsyncSessionFactory

async def seed_erp_data_if_needed():
    async with TestAsyncSessionFactory() as test_session:
        stmt_check = select(Dispatch).where(Dispatch.dispatch_date.is_not(None))
        res_check = await test_session.execute(stmt_check)
        valid_count = len(list(res_check.scalars().all()))
        if valid_count >= 50:
            return

    # Create isolated NullPool engine for prod reading
    prod_engine = create_async_engine(settings.ASYNC_DATABASE_URI, poolclass=NullPool)
    ProdSession = async_sessionmaker(prod_engine, expire_on_commit=False)

    async with ProdSession() as prod_session:
        plants = list((await prod_session.execute(select(Plant))).scalars().all())
        sites = list((await prod_session.execute(select(Site))).scalars().all())
        customers = list((await prod_session.execute(select(Customer))).scalars().all())
        vehicles = list((await prod_session.execute(select(Vehicle))).scalars().all())
        drivers = list((await prod_session.execute(select(Driver))).scalars().all())
        orders = list((await prod_session.execute(select(Order))).scalars().all())
        tickets = list((await prod_session.execute(select(Ticket))).scalars().all())
        dispatches = list((await prod_session.execute(select(Dispatch))).scalars().all())

    await prod_engine.dispose()

    async with TestAsyncSessionFactory() as test_session:
        await test_session.execute(delete(Dispatch))
        await test_session.execute(delete(Ticket))
        await test_session.execute(delete(Order))
        await test_session.execute(delete(Driver))
        await test_session.execute(delete(Vehicle))
        await test_session.execute(delete(Customer))
        await test_session.execute(delete(Site))
        await test_session.execute(delete(Plant))
        await test_session.commit()

        for p in plants:
            d = {k: v for k, v in p.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Plant(**d))
        for st in sites:
            d = {k: v for k, v in st.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Site(**d))
        for c in customers:
            d = {k: v for k, v in c.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Customer(**d))
        for v in vehicles:
            d = {k: v for k, v in v.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Vehicle(**d))
        for dr in drivers:
            d = {k: v for k, v in dr.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Driver(**d))
        for o in orders:
            d = {k: v for k, v in o.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Order(**d))
        for t in tickets:
            d = {k: v for k, v in t.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Ticket(**d))
        for disp in dispatches:
            d = {k: v for k, v in disp.__dict__.items() if k != "_sa_instance_state"}
            test_session.add(Dispatch(**d))

        try:
            await test_session.commit()
            print("[TEST SEED] Cleanly seeded all ERP dispatches and dependencies into test DB.")
        except Exception as e:
            await test_session.rollback()
            import traceback
            traceback.print_exc()
