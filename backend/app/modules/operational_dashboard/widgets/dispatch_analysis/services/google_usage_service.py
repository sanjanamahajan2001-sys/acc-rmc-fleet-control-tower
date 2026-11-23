"""
WS-ROUT-USAGE: Google Maps & Routes API Usage Tracking Service
Calculates monthly billable volume, cached savings, allowance percentage, and financial estimates.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import calendar
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.operational_dashboard.models.google_api_usage import GoogleApiUsageLog
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    GoogleApiUsageSummaryDTO,
)
from app.modules.settings.models import PlatformConfiguration

logger = get_logger("app.dispatch_analysis.google_usage")

# Default GCP Maps monthly recurring credit equivalent (20,000 route matrix elements)
DEFAULT_MONTHLY_ALLOWANCE = 20_000


class GoogleApiUsageService:
    """
    Authoritative service tracking and aggregating Google Maps & Routes API consumption.
    """

    @classmethod
    async def record_usage(
        cls,
        session: AsyncSession,
        api_service: str,
        endpoint: str,
        request_count: int = 1,
        status_code: int = 200,
        is_cached: bool = False,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Records an outgoing API request asynchronously.
        Guarantees zero interruption to calling services if database write fails.
        """
        try:
            log_entry = GoogleApiUsageLog(
                api_service=api_service,
                endpoint=endpoint,
                request_count=request_count,
                status_code=status_code,
                is_cached=is_cached,
                latency_ms=latency_ms,
            )
            session.add(log_entry)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.warning("Failed to record Google API usage telemetry log", error=str(exc))

    @classmethod
    async def get_monthly_usage_summary(
        cls,
        session: AsyncSession,
    ) -> GoogleApiUsageSummaryDTO:
        """
        Aggregates current calendar month usage, remaining allowance, and caching savings.
        """
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        _, last_day = calendar.monthrange(now.year, now.month)
        end_of_month = datetime(now.year, now.month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        # 1. Fetch configured monthly allowance from platform_configurations if set
        monthly_limit = DEFAULT_MONTHLY_ALLOWANCE
        try:
            async with session.begin_nested():
                stmt_config = select(PlatformConfiguration).where(
                    PlatformConfiguration.domain == "telemetry",
                    PlatformConfiguration.key == "google_maps_monthly_request_quota",
                )
                config_res = (await session.execute(stmt_config)).scalars().first()
                if config_res and config_res.value is not None:
                    if isinstance(config_res.value, (int, float)):
                        monthly_limit = int(config_res.value)
                    elif isinstance(config_res.value, str) and config_res.value.isdigit():
                        monthly_limit = int(config_res.value)
        except Exception:
            monthly_limit = DEFAULT_MONTHLY_ALLOWANCE

        # 2. Query total non-cached (billable) requests this month
        stmt_billable = select(
            func.coalesce(func.sum(GoogleApiUsageLog.request_count), 0),
            func.max(GoogleApiUsageLog.created_at),
        ).where(
            GoogleApiUsageLog.created_at >= start_of_month,
            GoogleApiUsageLog.created_at <= end_of_month,
            GoogleApiUsageLog.is_cached == False,
        )
        billable_res = (await session.execute(stmt_billable)).first()
        total_billable = int(billable_res[0]) if billable_res else 0
        last_queried = billable_res[1].isoformat() if billable_res and billable_res[1] else None

        # 3. Query total cached requests saved this month
        stmt_cached = select(
            func.coalesce(func.sum(GoogleApiUsageLog.request_count), 0)
        ).where(
            GoogleApiUsageLog.created_at >= start_of_month,
            GoogleApiUsageLog.created_at <= end_of_month,
            GoogleApiUsageLog.is_cached == True,
        )
        cached_res = (await session.execute(stmt_cached)).scalar()
        cached_saved = int(cached_res) if cached_res else 0

        # 4. Check if API key is configured
        api_key = getattr(settings, "GOOGLE_MAPS_ROUTES_API_KEY", "")
        is_configured = bool(api_key and api_key.strip())

        # 5. Compute metrics
        remaining = max(0, monthly_limit - total_billable)
        usage_pct = round((total_billable / monthly_limit) * 100, 1) if monthly_limit > 0 else 0.0

        if not is_configured:
            status = "UNCONFIGURED"
        elif usage_pct >= 100.0:
            status = "EXCEEDED"
        elif usage_pct >= 90.0:
            status = "CRITICAL"
        elif usage_pct >= 70.0:
            status = "WARNING"
        else:
            status = "HEALTHY"

        # Estimated cost calculation: Standard Routes Matrix / Directions is $5.00 per 1,000 requests after the $200 free credit (~40k base requests)
        # Here we estimate any requests exceeding the monthly free tier
        billable_excess = max(0, total_billable - monthly_limit)
        estimated_cost = round((billable_excess / 1000.0) * 5.0, 2)

        return GoogleApiUsageSummaryDTO(
            total_billable_requests_month=total_billable,
            cached_requests_saved_month=cached_saved,
            monthly_allowance_limit=monthly_limit,
            remaining_allowance=remaining,
            usage_percentage=usage_pct,
            status=status,
            is_api_configured=is_configured,
            billing_cycle_start=start_of_month.isoformat(),
            billing_cycle_end=end_of_month.isoformat(),
            last_queried_at=last_queried,
            estimated_cost_usd=estimated_cost,
        )
