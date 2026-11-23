import pytest_asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    test_engine = create_async_engine(settings.ASYNC_DATABASE_URI, poolclass=NullPool)
    TestSessionMaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSessionMaker() as session:
        yield session
    await test_engine.dispose()

