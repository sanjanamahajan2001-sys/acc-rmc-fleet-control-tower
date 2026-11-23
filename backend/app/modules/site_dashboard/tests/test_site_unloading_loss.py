import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.services.site_unloading_loss_service import SiteUnloadingLossService
from app.modules.site_dashboard.dto.canonical_dtos import SiteUnloadingLossResponseDTO


@pytest.mark.asyncio
async def test_site_unloading_loss_service_evaluations():
    """Verify SiteUnloadingLossService returns valid per-client breakdown and empty state handling."""
    async with AsyncSessionFactory() as session:
        # Test 1: Global evaluation
        res: SiteUnloadingLossResponseDTO = await SiteUnloadingLossService.get_unloading_loss_breakdown(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "ALL"}
        )

        assert res is not None
        assert res.total_affected_clients > 0
        assert len(res.data) == res.total_affected_clients

        # Verify Rank 1 row structure
        top_row = res.data[0]
        assert top_row.rank == 1
        assert top_row.affected_trips > 0
        assert top_row.avg_excess_unloading_mins > 0
        assert top_row.total_excess_unloading_mins > 0
        assert ":" in top_row.total_excess_unloading_formatted
        assert top_row.diesel_overhead_cost > 0.0

        # Test 2: Non-existent customer evaluation
        res_empty: SiteUnloadingLossResponseDTO = await SiteUnloadingLossService.get_unloading_loss_breakdown(
            session, {"plant_id": "ALL", "customer_id": "NON_EXISTENT", "dataset_type": "ALL"}
        )

        assert res_empty is not None
        assert res_empty.total_affected_clients == 0
        assert len(res_empty.data) == 0
