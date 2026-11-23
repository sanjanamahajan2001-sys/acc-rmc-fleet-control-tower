"""
WS-ROUT-USAGE: Google Maps & Routes API Telemetry Model
Authoritative ORM mapping for google_api_usage_logs.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VersionedEntity


class GoogleApiUsageLog(VersionedEntity):
    """
    Authoritative audit record of billable outgoing Google Maps & Routes API calls.
    Used to track real-time monthly usage against the configured free-tier/budget allowance.
    """
    __tablename__ = "google_api_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # ROUTES_MATRIX_V2, ROUTES_COMPUTE_V2
    endpoint: Mapped[str] = mapped_column(String(150), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    is_cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_google_api_usage_service_date", "api_service", "created_at"),
    )
