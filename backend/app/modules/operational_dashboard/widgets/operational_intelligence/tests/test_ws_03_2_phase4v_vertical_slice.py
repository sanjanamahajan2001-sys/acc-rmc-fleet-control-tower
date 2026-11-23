import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness import SiteReadinessEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import SiteReadinessResponseDTO, OperationalIntelligenceStatusEnum

@pytest.mark.asyncio
async def test_ws_03_2_phase4v_end_to_end_vertical_slice():
    """
    WS-03.2 Phase 4V End-to-End Vertical Slice Verification Test.
    Proves PostgreSQL -> Repository -> Engine -> API DTO 5-layer equality across 5 mandatory scopes.
    """
    async with AsyncSessionFactory() as session:
        # 1. Scope V-01: Global Scope (ALL / ALL / REAL_ONLY)
        filters_v01 = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_v01: SiteReadinessResponseDTO = await SiteReadinessEngine.get_site_readiness(session, filters_v01)
        assert res_v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v01.total_sites == 10
        top1_v01 = res_v01.data[0]
        assert top1_v01.site_id == "CUST_COUTINHO_N_ASSOCIATES"
        assert top1_v01.total_trips == 1
        assert top1_v01.swi_site == 0.0
        assert top1_v01.dpi_site == 0.0
        assert top1_v01.fui_site == 4.2
        assert top1_v01.sri_score == 1.0
        assert top1_v01.grade == "GRADE_D"

        # 2. Scope V-02: Dharga Plant Scope (ACC_DHARGA / ALL / REAL_ONLY)
        filters_v02 = {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_v02: SiteReadinessResponseDTO = await SiteReadinessEngine.get_site_readiness(session, filters_v02)
        assert res_v02.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v02.total_sites == 10
        top1_v02 = res_v02.data[0]
        assert top1_v02.site_id == "CUST_PREMIER_BULIDER"
        assert top1_v02.total_trips == 1
        assert top1_v02.fui_site == 14.3
        assert top1_v02.sri_score == 3.6

        # 3. Scope V-03: Vasco Plant Scope (ACC_VASCO / ALL / REAL_ONLY)
        filters_v03 = {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_v03: SiteReadinessResponseDTO = await SiteReadinessEngine.get_site_readiness(session, filters_v03)
        assert res_v03.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v03.total_sites == 10
        top1_v03 = res_v03.data[0]
        assert top1_v03.site_id == "CUST_MARCON"
        assert top1_v03.total_trips == 1
        assert top1_v03.fui_site == 14.3
        assert top1_v03.sri_score == 3.6

        # 4. Scope V-04: Customer Scope (ACC_KUNDAIM / CUST_AARA_HOTELS / REAL_ONLY)
        filters_v04 = {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}
        res_v04: SiteReadinessResponseDTO = await SiteReadinessEngine.get_site_readiness(session, filters_v04)
        assert res_v04.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_v04.total_sites == 1
        top1_v04 = res_v04.data[0]
        assert top1_v04.site_id == "CUST_AARA_HOTELS"
        assert top1_v04.total_trips == 3
        assert top1_v04.swi_site == 92.7
        assert top1_v04.dpi_site == 0.0
        assert top1_v04.fui_site == 12.5
        assert top1_v04.sri_score == 40.2

        # 5. Scope V-05: Synthetic Scope (ALL / ALL / SYNTHETIC_ONLY)
        filters_v05 = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        res_v05: SiteReadinessResponseDTO = await SiteReadinessEngine.get_site_readiness(session, filters_v05)
        assert res_v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert res_v05.total_sites == 0
        assert res_v05.data == []
