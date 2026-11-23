import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.services.site_retention_loss_service import SiteRetentionLossService
from app.modules.site_dashboard.dto.canonical_dtos import SiteRetentionLossResponseDTO


@pytest.mark.asyncio
async def test_site_retention_loss_service_evaluations():
    """Verify SiteRetentionLossService returns valid per-client breakdown and empty state handling."""
    async with AsyncSessionFactory() as session:
        # Test 1: Global evaluation
        res: SiteRetentionLossResponseDTO = await SiteRetentionLossService.get_retention_loss_breakdown(
            session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "ALL"}
        )

        assert res is not None
        assert res.total_affected_clients > 0
        assert len(res.data) == res.total_affected_clients

        # Verify Rank 1 row structure
        top_row = res.data[0]
        assert top_row.rank == 1
        assert top_row.affected_trips > 0
        assert top_row.avg_excess_retention_mins > 0
        assert top_row.total_excess_retention_mins > 0
        assert ":" in top_row.total_excess_retention_formatted

        # Test 2: Non-existent customer evaluation
        res_empty: SiteRetentionLossResponseDTO = await SiteRetentionLossService.get_retention_loss_breakdown(
            session, {"plant_id": "ALL", "customer_id": "NON_EXISTENT", "dataset_type": "ALL"}
        )

        assert res_empty is not None
        assert res_empty.total_affected_clients == 0
        assert len(res_empty.data) == 0
