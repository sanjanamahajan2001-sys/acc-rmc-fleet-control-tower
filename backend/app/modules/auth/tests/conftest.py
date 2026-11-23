import pytest_asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.dependencies.common import get_db_session
from app.main import app

test_engine = create_async_engine(settings.ASYNC_DATABASE_URI, poolclass=NullPool)
TestSessionMaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db_session():
    async with TestSessionMaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

app.dependency_overrides[get_db_session] = override_get_db_session

@pytest_asyncio.fixture
async def session() -> AsyncSession:
    async with TestSessionMaker() as session:
        yield session


