"""
WS-10 Phase 3: Authoritative Calculation Rate Configuration Entity
Defines PostgreSQL ORM entity mapping for `CalculationRateConfiguration` (`calculation_rate_configurations`).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditEntity


class CalculationRateConfiguration(AuditEntity):
    """
    Authoritative Rate Configuration Entity (`calculation_rate_configurations`).
    Provides effective-dated, hierarchical rate rules for financial exposure, SLA breach penalties,
    and fleet idle cost calculations.
    """

    __tablename__ = "calculation_rate_configurations"

    rate_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    rate_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rate_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR", server_default=text("'INR'"))
    
    plant_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    customer_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    rate_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0", server_default=text("'v1.0.0'"))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)

    metadata_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "idx_rate_hierarchy_lookup",
            "rate_code",
            "plant_code",
            "customer_code",
            "effective_from",
            "is_active",
        ),
    )
