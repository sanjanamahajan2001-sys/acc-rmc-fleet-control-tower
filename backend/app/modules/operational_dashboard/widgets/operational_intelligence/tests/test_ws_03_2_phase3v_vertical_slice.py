import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.overlap_heatmap import OverlapHeatmapEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import OperationalIntelligenceStatusEnum

@pytest.mark.asyncio
async def test_vertical_slice_5_scopes_equality_overlap():
    async with AsyncSessionFactory() as session:
        # Scope 1: ALL / ALL / REAL_ONLY
        filters_1 = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_1 = await OverlapHeatmapEngine.get_overlap_heatmap(session, filters_1, limit=10)
        assert res_1.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_1.total_sites == 10
        assert res_1.data[0].site_id == "DEFAULT_CUSTOMER"
        assert res_1.data[0].total_trips == 2066
        assert res_1.data[0].peak_tms_together == 1874
        assert res_1.data[0].avg_tms_standing_together == 906.0
        assert res_1.data[0].overlap_hours == 47.3
        assert res_1.data[0].weighted_tm_minutes == 2568865.6

        # Scope 2: ACC_DHARGA / ALL / REAL_ONLY
        filters_2 = {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_2 = await OverlapHeatmapEngine.get_overlap_heatmap(session, filters_2, limit=10)
        assert res_2.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_2.total_sites == 10
        assert res_2.data[0].site_id == "DEFAULT_CUSTOMER"
        assert res_2.data[0].total_trips == 331
        assert res_2.data[0].peak_tms_together == 320
        assert res_2.data[0].avg_tms_standing_together == 151.1
        assert res_2.data[0].overlap_hours == 47.1
        assert res_2.data[0].weighted_tm_minutes == 423835.2

        # Scope 3: ACC_VASCO / ALL / REAL_ONLY
        filters_3 = {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}
        res_3 = await OverlapHeatmapEngine.get_overlap_heatmap(session, filters_3, limit=10)
        assert res_3.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_3.total_sites == 10
        assert res_3.data[0].site_id == "DEFAULT_CUSTOMER"
        assert res_3.data[0].total_trips == 850
        assert res_3.data[0].peak_tms_together == 808
        assert res_3.data[0].avg_tms_standing_together == 396.5
        assert res_3.data[0].overlap_hours == 45.4
        assert res_3.data[0].weighted_tm_minutes == 1077790.2

        # Scope 4: ACC_KUNDAIM / CUST_AARA_HOTELS / REAL_ONLY
        filters_4 = {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}
        res_4 = await OverlapHeatmapEngine.get_overlap_heatmap(session, filters_4, limit=10)
        assert res_4.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_4.total_sites == 1
        assert res_4.data[0].site_id == "CUST_AARA_HOTELS"
        assert res_4.data[0].total_trips == 3
        assert res_4.data[0].peak_tms_together == 3
        assert res_4.data[0].avg_tms_standing_together == 2.7
        assert res_4.data[0].overlap_hours == 18.8
        assert res_4.data[0].weighted_tm_minutes == 1878.5

        # Scope 5: ALL / ALL / SYNTHETIC_ONLY
        filters_5 = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        res_5 = await OverlapHeatmapEngine.get_overlap_heatmap(session, filters_5, limit=10)
        assert res_5.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert res_5.total_sites == 0
        assert res_5.data == []
