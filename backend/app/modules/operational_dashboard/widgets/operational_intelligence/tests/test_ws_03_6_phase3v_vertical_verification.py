import pytest
import pytest_asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.customer_efficiency import CustomerEfficiencyEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import OperationalIntelligenceStatusEnum

@pytest.mark.asyncio
async def test_vertical_slice_5_scopes():
    """Verify all 5 vertical verification scopes in a single async event loop."""
    async with AsyncSessionFactory() as session:
        # V-01 Global
        v01 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ALL', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v01.success is True
        assert v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v01.data) == 204
        top1_v01 = v01.data[0]
        assert top1_v01.rank == 1
        assert top1_v01.customer_id == "CUST_DAFTARY_DESCON_ENGG_PVT_LTD_DECCAN"
        assert top1_v01.cei_score == 0.0
        assert top1_v01.grade == "Critical"
        assert top1_v01.trend == "FLAT"

        # V-02 Dharga
        v02 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ACC_DHARGA', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v02.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v02.data) == 113
        top1_v02 = v02.data[0]
        assert top1_v02.rank == 1
        assert top1_v02.customer_id == "CUST_RAJ_CHOPRA_N_COMPANY"

        # V-03 Vasco
        v03 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ACC_VASCO', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v03.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v03.data) == 68
        top1_v03 = v03.data[0]
        assert top1_v03.rank == 1
        assert top1_v03.customer_id == "CUST_KENKRE_ELECTRICAL"

        # V-04 Customer Specific
        v04 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ACC_KUNDAIM', 'customer_id': 'CUST_AARA_HOTELS', 'dataset_type': 'REAL_ONLY'}
        )
        assert v04.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v04.data) == 1
        top1_v04 = v04.data[0]
        assert top1_v04.rank == 1
        assert top1_v04.customer_id == "CUST_AARA_HOTELS"
        assert top1_v04.cei_score == 87.8
        assert top1_v04.grade == "Good"

        # V-05 Synthetic Scope (Honest NO_OBSERVATIONS)
        v05 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ALL', 'customer_id': 'ALL', 'dataset_type': 'SYNTHETIC_ONLY'}
        )
        assert v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert len(v05.data) == 0
