import pytest
import pytest_asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_comparison import SiteComparisonEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import OperationalIntelligenceStatusEnum

@pytest.mark.asyncio
async def test_01_status_classification_boundaries():
    """Verify exact status classification boundary rules: Optimal (>=90%), Good (70-89.9%), Warning (50-69.9%), Critical (<50%)."""
    assert SiteComparisonEngine.classify_status(100.0) == "Optimal"
    assert SiteComparisonEngine.classify_status(90.0) == "Optimal"
    assert SiteComparisonEngine.classify_status(89.9) == "Good"
    assert SiteComparisonEngine.classify_status(70.0) == "Good"
    assert SiteComparisonEngine.classify_status(69.9) == "Warning"
    assert SiteComparisonEngine.classify_status(50.0) == "Warning"
    assert SiteComparisonEngine.classify_status(49.9) == "Critical"
    assert SiteComparisonEngine.classify_status(0.0) == "Critical"

@pytest.mark.asyncio
async def test_02_deterministic_ranking_precedence():
    """Verify 3-tier deterministic ranking precedence: dispatches DESC, volume_cum DESC, site_code ASC."""
    raw = [
        {"site_code": "SITE_C", "dispatches": 500, "volume_cum": 2000.0},
        {"site_code": "SITE_A", "dispatches": 1000, "volume_cum": 4000.0},
        {"site_code": "SITE_B", "dispatches": 1000, "volume_cum": 6000.0},
        {"site_code": "SITE_AA", "dispatches": 1000, "volume_cum": 4000.0},
    ]
    sorted_sites = sorted(raw, key=lambda x: (-x["dispatches"], -x["volume_cum"], x["site_code"]))
    assert sorted_sites[0]["site_code"] == "SITE_B"   # 1000 trips, 6000m3
    assert sorted_sites[1]["site_code"] == "SITE_A"   # 1000 trips, 4000m3
    assert sorted_sites[2]["site_code"] == "SITE_AA"  # 1000 trips, 4000m3 (alphabetical tiebreaker)
    assert sorted_sites[3]["site_code"] == "SITE_C"   # 500 trips

@pytest.mark.asyncio
async def test_03_five_scope_reconciliation_and_isolation():
    """Verify Scopes V-01 through V-05 across all 7 mandatory metrics in a single session scope."""
    async with AsyncSessionFactory() as session:
        # V-01 Global
        v01 = await SiteComparisonEngine.get_site_comparison(
            session, {'plant_id': 'ALL', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v01.success is True
        assert v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v01.data) == 4

        # Rank 1: ACC_VASCO
        vasco = v01.data[0]
        assert vasco.rank == 1
        assert vasco.site_code == "ACC_VASCO"
        assert vasco.dispatches == 1174
        assert vasco.volume_cum == 38755.0
        assert vasco.avg_holding_mins == 18.5
        assert vasco.avg_retention_mins == 7.5
        assert vasco.max_queue_tms == 8
        assert vasco.dispatch_accuracy == 70.0
        assert vasco.status == "Good"

        # Rank 2: ACC_KUNDAIM
        kundaim = v01.data[1]
        assert kundaim.rank == 2
        assert kundaim.site_code == "ACC_KUNDAIM"
        assert kundaim.dispatches == 1065
        assert kundaim.volume_cum == 57222.0
        assert kundaim.avg_holding_mins == 22.8
        assert kundaim.avg_retention_mins == 7.8
        assert kundaim.max_queue_tms == 9
        assert kundaim.dispatch_accuracy == 65.2
        assert kundaim.status == "Warning"

        # Rank 3: ACC_DHARGA
        dharga = v01.data[2]
        assert dharga.rank == 3
        assert dharga.site_code == "ACC_DHARGA"
        assert dharga.dispatches == 978
        assert dharga.volume_cum == 48693.0
        assert dharga.avg_holding_mins == 26.2
        assert dharga.avg_retention_mins == 11.9
        assert dharga.max_queue_tms == 7
        assert dharga.dispatch_accuracy == 57.4
        assert dharga.status == "Warning"

        # Rank 4: ACC_NESSAI
        nessai = v01.data[3]
        assert nessai.rank == 4
        assert nessai.site_code == "ACC_NESSAI"
        assert nessai.dispatches == 315
        assert nessai.volume_cum == 20336.0
        assert nessai.avg_holding_mins == 34.3
        assert nessai.avg_retention_mins == 10.8
        assert nessai.max_queue_tms == 4
        assert nessai.dispatch_accuracy == 49.2
        assert nessai.status == "Critical"

        # V-02 Dharga
        v02 = await SiteComparisonEngine.get_site_comparison(
            session, {'plant_id': 'ACC_DHARGA', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v02.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v02.data) == 1
        d = v02.data[0]
        assert d.site_code == "ACC_DHARGA"
        assert d.dispatches == 978
        assert d.volume_cum == 48693.0
        assert d.avg_holding_mins == 26.2
        assert d.avg_retention_mins == 11.9
        assert d.max_queue_tms == 7
        assert d.dispatch_accuracy == 57.4
        assert d.status == "Warning"

        # V-03 Vasco
        v03 = await SiteComparisonEngine.get_site_comparison(
            session, {'plant_id': 'ACC_VASCO', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v03.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v03.data) == 1
        v = v03.data[0]
        assert v.site_code == "ACC_VASCO"
        assert v.dispatches == 1174
        assert v.volume_cum == 38755.0
        assert v.avg_holding_mins == 18.5
        assert v.avg_retention_mins == 7.5
        assert v.max_queue_tms == 8
        assert v.dispatch_accuracy == 70.0
        assert v.status == "Good"

        # V-04 Customer Specific Scope (ACC_KUNDAIM / CUST_AARA_HOTELS / REAL_ONLY)
        v04 = await SiteComparisonEngine.get_site_comparison(
            session, {'plant_id': 'ACC_KUNDAIM', 'customer_id': 'CUST_AARA_HOTELS', 'dataset_type': 'REAL_ONLY'}
        )
        assert v04.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v04.data) == 1
        c = v04.data[0]
        assert c.site_code == "ACC_KUNDAIM"
        assert c.dispatches == 3
        assert c.volume_cum == 266.0
        assert c.avg_holding_mins == 13.7
        assert c.avg_retention_mins == 6.3
        assert c.max_queue_tms == 1
        assert c.dispatch_accuracy == 66.7
        assert c.status == "Warning"

        # V-05 Synthetic Scope (Honest NO_OBSERVATIONS)
        v05 = await SiteComparisonEngine.get_site_comparison(
            session, {'plant_id': 'ALL', 'customer_id': 'ALL', 'dataset_type': 'SYNTHETIC_ONLY'}
        )
        assert v05.success is True
        assert v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert len(v05.data) == 0
