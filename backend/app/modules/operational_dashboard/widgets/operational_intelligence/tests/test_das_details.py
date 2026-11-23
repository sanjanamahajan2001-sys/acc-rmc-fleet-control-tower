import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.das_details import DASDetailsEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    DASDetailsResponseDTO,
    OperationalIntelligenceStatusEnum,
)


@pytest.mark.asyncio
async def test_das_details_all_scopes():
    scopes = [
        ("V-01 Global", {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}, 3532, 2232, 674, 626, 63.2, 204),
        ("V-02 Dharga", {"plant_id": "ACC_DHARGA", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}, 978, 561, 212, 205, 57.4, 113),
        ("V-03 Vasco", {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}, 1174, 822, 191, 161, 70.0, 68),
        ("V-04 Customer", {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}, 3, 2, 1, 0, 66.7, 1),
    ]

    async with AsyncSessionFactory() as session:
        for name, filters, exp_tot, exp_acc, exp_mod, exp_crit, exp_das, exp_cust_cnt in scopes:
            details_dto: DASDetailsResponseDTO = await DASDetailsEngine.evaluate_details(session, filters)

            assert details_dto.status == OperationalIntelligenceStatusEnum.AVAILABLE, f"Failed status on {name}"
            assert details_dto.summary.total_dispatches == exp_tot, f"Failed total dispatches on {name}"
            assert details_dto.summary.accurate_dispatches == exp_acc, f"Failed accurate dispatches on {name}"
            assert details_dto.summary.das_score == exp_das, f"Failed DAS score on {name}"
            assert len(details_dto.data) == exp_cust_cnt, f"Failed customer count on {name}"

            # DETAIL <-> OVERVIEW RECONCILIATION EQUALITY
            sum_tot = sum(r.total_dispatches for r in details_dto.data)
            sum_acc = sum(r.accurate_count for r in details_dto.data)
            sum_mod = sum(r.moderate_count for r in details_dto.data)
            sum_crit = sum(r.critical_count for r in details_dto.data)

            assert sum_tot == exp_tot, f"Failed SUM(detail.total_dispatches) on {name}"
            assert sum_acc == exp_acc, f"Failed SUM(detail.accurate_count) on {name}"
            assert sum_mod == exp_mod, f"Failed SUM(detail.moderate_count) on {name}"
            assert sum_crit == exp_crit, f"Failed SUM(detail.critical_count) on {name}"

            for r in details_dto.data:
                assert r.accurate_count + r.moderate_count + r.critical_count == r.total_dispatches, f"Row sum mismatch for customer {r.customer_id}"

        # Synthetic Scope Test
        synth_filters = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}
        synth_dto: DASDetailsResponseDTO = await DASDetailsEngine.evaluate_details(session, synth_filters)

        assert synth_dto.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert synth_dto.total_customers == 0
        assert len(synth_dto.data) == 0
        assert synth_dto.summary.das_score is None
