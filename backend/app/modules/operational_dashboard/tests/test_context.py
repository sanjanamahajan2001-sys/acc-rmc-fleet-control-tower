import pytest
import time
from fastapi import HTTPException
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService

@pytest.mark.asyncio
async def test_operational_context_service_all_tests():
    async with AsyncSessionFactory() as session:
        # Warmup connection
        params_warm = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="REAL_ONLY")
        await OperationalContextService.get_shell_context(session, params_warm)

        # Test 1: Default Context SLA
        t0 = time.perf_counter()
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="REAL_ONLY")
        res = await OperationalContextService.get_shell_context(session, params)
        t1 = time.perf_counter()
        dur_ms = (t1 - t0) * 1000.0

        assert res is not None
        assert res.context.plant_id == "ALL"
        assert res.context.customer_id == "ALL"
        assert res.context.dataset_type == "REAL_ONLY"
        assert res.context.dataset_id is not None
        assert res.context.snapshot_version is not None
        assert res.metadata["total_dispatches"] >= 0
        assert len(res.available_plants) >= 1
        assert len(res.available_customers) >= 1
        assert dur_ms < 100.0, f"Operational context duration {dur_ms}ms exceeds 100ms SLA"

        # Test 2: Invalid Plant (404)
        invalid_plant_params = DashboardFilterParams(plant_id="INVALID_PLANT_CODE_999", customer_id="ALL", dataset_type="ALL")
        with pytest.raises(HTTPException) as exc_info1:
            await OperationalContextService.get_shell_context(session, invalid_plant_params)
        assert exc_info1.value.status_code == 404
        assert "Plant identifier 'INVALID_PLANT_CODE_999' not found" in exc_info1.value.detail

        # Test 3: Invalid Customer (404)
        invalid_cust_params = DashboardFilterParams(plant_id="ALL", customer_id="INVALID_CUST_CODE_999", dataset_type="ALL")
        with pytest.raises(HTTPException) as exc_info2:
            await OperationalContextService.get_shell_context(session, invalid_cust_params)
        assert exc_info2.value.status_code == 404
        assert "Customer identifier 'INVALID_CUST_CODE_999' not found" in exc_info2.value.detail

        # Test 4: Invalid Dataset Type (422)
        invalid_type_params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="INVALID_TYPE")
        with pytest.raises(HTTPException) as exc_info3:
            await OperationalContextService.get_shell_context(session, invalid_type_params)
        assert exc_info3.value.status_code == 422
        assert "Invalid dataset_type 'INVALID_TYPE'" in exc_info3.value.detail

        # Test 5: Synthetic Only Zero State
        synthetic_params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="SYNTHETIC_ONLY")
        res_synth = await OperationalContextService.get_shell_context(session, synthetic_params)
        assert res_synth.context.dataset_type == "SYNTHETIC_ONLY"
        assert res_synth.metadata["total_dispatches"] == 0
