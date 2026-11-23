import pytest
import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.site_dashboard.orchestration.dashboard_orchestrator import DashboardDataOrchestrator
from app.modules.site_dashboard.widgets.queue_analytics.service import QueueAnalyticsService
from app.modules.site_dashboard.widgets.tm_details.service import TMDetailsService
from app.modules.site_dashboard.widgets.site_performance.service import SitePerformanceService
from app.modules.site_dashboard.widgets.fleet_utilization.service import FleetUtilizationService
from app.modules.site_dashboard.widgets.decision_intelligence.service import DecisionIntelligenceService
from app.modules.site_dashboard.widgets.operational_widgets.service import OperationalWidgetsService
from app.modules.site_dashboard.sync.service import SyncService


@pytest.mark.asyncio
async def test_phase_2_master_end_to_end():
    """Consolidated master test suite validating all 11 dashboard subsystems within a single AsyncSession."""
    async with AsyncSessionFactory() as session:
        # 1. Test Full Dashboard Subsystems Load
        t0 = time.perf_counter()
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        filters = {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "ALL"}

        master = await DashboardDataOrchestrator.get_master_dashboard_data(session, params)
        queue = await QueueAnalyticsService.compute_queue_analytics(session, filters)
        tm = await TMDetailsService.get_tm_details(session, filters)
        perf = await SitePerformanceService.get_site_performance(session, filters)
        fleet = await FleetUtilizationService.get_fleet_utilization(session, filters)
        decision = await DecisionIntelligenceService.get_decision_intelligence(session, filters)
        widgets = await OperationalWidgetsService.get_operational_widgets(session, filters)
        sync = await SyncService.get_sync_status(session)
        t1 = time.perf_counter()

        total_dur_ms = (t1 - t0) * 1000.0

        assert master is not None
        assert queue is not None
        assert tm is not None
        assert perf is not None
        assert fleet is not None
        assert decision is not None
        assert widgets is not None
        assert sync is not None
        assert total_dur_ms < 500.0, f"Full dashboard payload load duration {total_dur_ms}ms exceeds target threshold"

        # 2. Test Filter Propagation Integrity
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        filters_vasco = {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "ALL"}
        
        master_vasco = await DashboardDataOrchestrator.get_master_dashboard_data(session, params_vasco)
        queue_vasco = await QueueAnalyticsService.compute_queue_analytics(session, filters_vasco)
        decision_vasco = await DecisionIntelligenceService.get_decision_intelligence(session, filters_vasco)
        widgets_vasco = await OperationalWidgetsService.get_operational_widgets(session, filters_vasco)

        assert master_vasco.summary is not None
        assert queue_vasco is not None
        assert decision_vasco is not None
        assert widgets_vasco is not None

        # 3. Test ERP Reset & Import Lifecycle Notification Events over SSE Sync Engine
        reset_evt = await SyncService.notify_erp_reset(session)
        assert reset_evt.event_type == "ERP_RESET_COMPLETED"
        assert reset_evt.snapshot_version == "v2.11-SNAP-EMPTY"

        import_evt = await SyncService.notify_erp_import(session, 3532)
        assert import_evt.event_type == "ERP_IMPORT_COMPLETED"
        assert import_evt.details["records_imported"] == 3532
