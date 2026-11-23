import pytest
import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.problem_customers import ProblemCustomersEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import OperationalIntelligenceStatusEnum

@pytest.mark.asyncio
async def test_vertical_slice_5_scopes_equality():
    async with AsyncSessionFactory() as session:
        # Scope 1: ALL / ALL / REAL_ONLY
        filters_1 = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_1 = await ProblemCustomersEngine.get_top_problem_customers(session, filters_1, limit=10)
        assert res_1.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_1.total_count == 10
        assert res_1.data[0].customer_id == "DEFAULT_CUSTOMER"
        assert res_1.data[0].total_lost_hours == 449.1
        assert res_1.data[0].cei == 56.5

        # Scope 2: ACC_DHARGA / ALL / REAL_ONLY
        filters_2 = {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_2 = await ProblemCustomersEngine.get_top_problem_customers(session, filters_2, limit=10)
        assert res_2.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_2.total_count == 10
        assert res_2.data[0].customer_id == "DEFAULT_CUSTOMER"
        assert res_2.data[0].total_lost_hours == 64.0
        assert res_2.data[0].cei == 61.3

        # Scope 3: ACC_VASCO / ALL / REAL_ONLY
        filters_3 = {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_3 = await ProblemCustomersEngine.get_top_problem_customers(session, filters_3, limit=10)
        assert res_3.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_3.total_count == 10
        assert res_3.data[0].customer_id == "DEFAULT_CUSTOMER"
        assert res_3.data[0].total_lost_hours == 127.2
        assert res_3.data[0].cei == 70.1

        # Scope 4: ACC_KUNDAIM / CUST_AARA_HOTELS / REAL_ONLY
        filters_4 = {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}
        res_4 = await ProblemCustomersEngine.get_top_problem_customers(session, filters_4, limit=10)
        assert res_4.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_4.total_count == 1
        assert res_4.data[0].customer_id == "CUST_AARA_HOTELS"
        assert res_4.data[0].total_lost_hours == 0.2
        assert res_4.data[0].cei == 87.8

        # Scope 5: ALL / ALL / SYNTHETIC_ONLY
        filters_5 = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        res_5 = await ProblemCustomersEngine.get_top_problem_customers(session, filters_5, limit=10)
        assert res_5.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert res_5.total_count == 0
        assert res_5.data == []
