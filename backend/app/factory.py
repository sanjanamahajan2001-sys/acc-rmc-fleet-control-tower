"""
Application Factory Pattern

Initializes FastAPI application instance, registers startup validation & shutdown cleanup,
middleware chain (CORS, RequestLogging, CorrelationID, AuthenticationMiddleware),
router hierarchy, global exception handlers, and custom OpenAPI schema.
Updated in WS-07.9 to register and manage background Cron scheduler & alert archival task.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import main_router, fleet_router
from app.core.database import check_database_health, engine, AsyncSessionFactory
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIDMiddleware, ForcedPasswordChangeMiddleware, RequestLoggingMiddleware

from app.core.openapi import setup_openapi
from app.core.security.middleware import AuthenticationMiddleware
from app.workers.scheduler import scheduler_instance
from app.modules.operational_dashboard.widgets.alerts.service import AlertService, RESOLVED_OPERATIONAL_RETENTION_HOURS

logger = get_logger("app.factory")


async def scheduled_alert_archival_task() -> None:
    """Periodic scheduled task that runs alert archival on RESOLVED alerts older than retention policy."""
    try:
        async with AsyncSessionFactory() as session:
            count = await AlertService.archive_resolved_alerts(
                session=session,
                retention_hours=RESOLVED_OPERATIONAL_RETENTION_HOURS,
            )
            if count > 0:
                logger.info(f"[WS-07.9 Scheduler] Automated archival completed: {count} alerts archived.")
    except Exception as exc:
        logger.error(f"[WS-07.9 Scheduler] Automated archival failed: {exc}", exc_info=True)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Application lifespan context manager executing fail-fast startup readiness
    validation and graceful resource shutdown cleanup.
    """
    # 1. Initialize logging
    configure_logging()
    logger.info("Initializing Fleet Control Tower Backend Framework v1.0.0...")

    # 2. Fail-fast startup validation pinging PostgreSQL database pool
    try:
        db_health = await check_database_health()
        if db_health.get("status") != "healthy":
            raise RuntimeError("Database pool health check failed during startup")
        logger.info("Database startup health check PASSED", pool_metrics=db_health)
    except Exception as exc:
        logger.critical(
            "Fail-fast startup aborted: Database unavailable", error=str(exc)
        )
        raise RuntimeError(f"Startup readiness failed: {exc!s}") from exc

    # 3. Register & Start Global Scheduler (WS-07.9 Alert Retention Archival task every 3600 seconds)
    try:
        scheduler_instance.schedule_periodic_task(
            name="alert_lifecycle_archival",
            interval_seconds=3600.0,
            task=scheduled_alert_archival_task,
        )
        await scheduler_instance.start()
        logger.info("Background Cron Scheduler & Alert Archival Task STARTED")
    except Exception as exc:
        logger.error(f"Failed to start background Cron Scheduler: {exc}")

    # 4. Auto-Promote ML Models if non-promoted database state is detected
    try:
        async with AsyncSessionFactory() as session:
            from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
            from sqlalchemy import select
            res = await session.execute(select(MLModelVersion).where(MLModelVersion.lifecycle_status == "PROMOTED"))
            promoted_models = res.scalars().all()
            if len(promoted_models) == 0:
                logger.info("[ML Startup Authority] Seeding 4 PROMOTED models automatically...")
                try:
                    from seed_promoted_models import promote
                    await promote()
                    logger.info("[ML Startup Authority] Promoted models seeded. PREDICTION AUTHORITY = AUTHORITATIVE.")
                except Exception as seed_err:
                    logger.warning(f"[ML Startup Authority] ML model seeding skipped: {seed_err}")
    except Exception as exc:
        logger.warning(f"[ML Startup Authority] Failed to check ML models on startup: {exc}")

    yield

    # 4. Graceful shutdown sequence stopping scheduler & disposing database engine pool
    logger.info("Shutting down Fleet Control Tower Backend Framework...")
    try:
        await scheduler_instance.stop()
        logger.info("Background Cron Scheduler STOPPED cleanly")
    except Exception as exc:
        logger.error(f"Error stopping background Cron Scheduler: {exc}")

    await engine.dispose()
    logger.info("Database connection engine pool disposed cleanly")


def create_app() -> FastAPI:
    """
    Factory function creating and configuring the FastAPI application instance.
    """
    app = FastAPI(
        title="Fleet Control Tower Platform API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=app_lifespan,
    )

    # 1. Register Global CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    # 2. Register Middlewares in Execution Order
    app.add_middleware(ForcedPasswordChangeMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    # 3. Register Global Exception Handlers
    register_exception_handlers(app)

    # 4. Register Main API Router Hierarchy (/demo-api/v1 and /fleet-api/v1)
    app.include_router(main_router)
    app.include_router(fleet_router)

    # 5. Customize OpenAPI Specification Metadata
    setup_openapi(app)

    return app
