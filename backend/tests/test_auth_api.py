import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.factory import create_app
from app.core.database import AsyncSessionFactory
from app.modules.auth.models import User
from app.core.security.password import verify_password
from sqlalchemy import select

@pytest.mark.asyncio
async def test_admin_account_verification():
    async with AsyncSessionFactory() as session:
        user = (await session.execute(
            select(User).where(User.username == "admin")
        )).scalars().first()
        assert user is not None
        assert user.username == "admin"
        assert user.is_superuser is True
        assert verify_password("Admin@Fleet2026!", user.password_hash) is True
