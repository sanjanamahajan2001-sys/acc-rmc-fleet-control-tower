import pytest
from sqlalchemy import select, func
from app.modules.erp.models import Customer, Plant, Dispatch, CustomerDisplayOverride


@pytest.mark.asyncio
async def test_phase1_migration_integrity(db_session):
    cust_cnt = (await db_session.execute(select(func.count(Customer.id)))).scalar() or 0
    plant_cnt = (await db_session.execute(select(func.count(Plant.id)))).scalar() or 0
    disp_cnt = (await db_session.execute(select(func.count(Dispatch.id)))).scalar() or 0
    override_cnt = (await db_session.execute(select(func.count(CustomerDisplayOverride.id)))).scalar() or 0

    assert cust_cnt >= 204
    assert plant_cnt >= 4
    assert disp_cnt >= 3532

