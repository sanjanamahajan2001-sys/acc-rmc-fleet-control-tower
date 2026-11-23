import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_overview import DASOverviewEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    DASOverviewResponseDTO,
    OperationalIntelligenceStatusEnum,
)


@pytest.mark.asyncio
async def test_01_all_five_scopes_reconciliation():
    scopes = [
        ("V-01", {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}, 3532, 2232, 674, 626, 63.2, -26.8, "CRITICAL", OperationalIntelligenceStatusEnum.AVAILABLE),
        ("V-02", {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}, 978, 561, 212, 205, 57.4, -32.6, "CRITICAL", OperationalIntelligenceStatusEnum.AVAILABLE),
        ("V-03", {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}, 1174, 822, 191, 161, 70.0, -20.0, "CRITICAL", OperationalIntelligenceStatusEnum.AVAILABLE),
        ("V-04", {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}, 3, 2, 1, 0, 66.7, -23.3, "CRITICAL", OperationalIntelligenceStatusEnum.AVAILABLE),
        ("V-05", {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}, 0, 0, 0, 0, None, None, "NEUTRAL", OperationalIntelligenceStatusEnum.NO_OBSERVATIONS),
    ]

    async with AsyncSessionFactory() as session:
        for code, filters, exp_tot, exp_acc, exp_mod, exp_crit, exp_das, exp_var, exp_status, exp_avail in scopes:
            res: DASOverviewResponseDTO = await DASOverviewEngine.evaluate_overview(session, filters)

            assert res.status == exp_avail, f"Failed on {code}"
            assert res.summary.total_dispatches == exp_tot, f"Failed on {code}"
            assert res.summary.accurate_dispatches == exp_acc, f"Failed on {code}"
            assert res.summary.das_score == exp_das, f"Failed on {code}"
            assert res.summary.variance == exp_var, f"Failed on {code}"
            assert res.summary.operational_status == exp_status, f"Failed on {code}"

            assert res.buckets.within_20m_count == exp_acc, f"Failed on {code}"
            assert res.buckets.moderate_20_40m_count == exp_mod, f"Failed on {code}"
            assert res.buckets.critical_above_40m_count == exp_crit, f"Failed on {code}"
            assert res.buckets.within_20m_count + res.buckets.moderate_20_40m_count + res.buckets.critical_above_40m_count == exp_tot, f"Failed on {code}"
