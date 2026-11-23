import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionFactory
from app.modules.settings.models import PlatformConfiguration, ConfigurationCategory

@pytest.mark.asyncio
async def test_get_settings_categories_db():
    async with AsyncSessionFactory() as session:
        cats = (await session.execute(select(ConfigurationCategory))).scalars().all()
        assert len(cats) >= 12
        
        stmt = select(PlatformConfiguration).where(
            PlatformConfiguration.domain == "cost",
            PlatformConfiguration.key == "diesel_price_per_liter"
        )
        cfg = (await session.execute(stmt)).scalars().first()
        assert cfg is not None
