"""
API Version 1 Modular Router Registry

Aggregates all v1 API modules (Health, Auth, Settings, Site Dashboard, Operational Dashboard, ERP, Telemetry, Timeline Replay, Reports)
into a unified v1 router.
"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.erp.api.router import erp_router
from app.modules.telemetry.api.router import router as telemetry_router
from app.modules.auth.api.router import router as auth_router
from app.modules.auth.api.users_router import users_router

from app.modules.settings.api.router import router as settings_router
from app.modules.settings.api.customer_settings_router import customer_settings_router
from app.modules.site_dashboard.api.router import router as site_dashboard_router

from app.modules.site_dashboard.widgets.queue_analytics.routes import router as queue_analytics_router
from app.modules.site_dashboard.widgets.tm_details.routes import router as tm_details_router
from app.modules.site_dashboard.widgets.site_performance.routes import router as site_performance_router
from app.modules.site_dashboard.widgets.fleet_utilization.routes import router as fleet_utilization_router
from app.modules.site_dashboard.widgets.decision_intelligence.routes import router as decision_intelligence_router
from app.modules.site_dashboard.widgets.operational_widgets.routes import router as operational_widgets_router
from app.modules.site_dashboard.sync.routes import sync_router
from app.modules.operational_dashboard.api.routes import router as operational_dashboard_router
from app.modules.operational_dashboard.widgets.dispatch_analysis.routes import router as dispatch_analysis_router
from app.modules.operational_dashboard.widgets.dispatch_optimization.routes import router as dispatch_optimization_router
from app.modules.operational_dashboard.widgets.alerts.routes import router as alerts_router
from app.modules.operational_dashboard.widgets.timeline_replay.routes import router as timeline_replay_router
from app.modules.operational_intelligence.api.router import router as operational_intelligence_router
from app.modules.reports.api.router import reports_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(customer_settings_router)
v1_router.include_router(settings_router)

v1_router.include_router(site_dashboard_router)

v1_router.include_router(queue_analytics_router)
v1_router.include_router(tm_details_router)
v1_router.include_router(site_performance_router)
v1_router.include_router(fleet_utilization_router)
v1_router.include_router(decision_intelligence_router)
v1_router.include_router(operational_widgets_router)
v1_router.include_router(operational_dashboard_router)
v1_router.include_router(dispatch_analysis_router)
v1_router.include_router(dispatch_optimization_router)
v1_router.include_router(alerts_router)
v1_router.include_router(timeline_replay_router)
v1_router.include_router(operational_intelligence_router)
v1_router.include_router(reports_router)
v1_router.include_router(sync_router)
v1_router.include_router(erp_router)
v1_router.include_router(telemetry_router)
