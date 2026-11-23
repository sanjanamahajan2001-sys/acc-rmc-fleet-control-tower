"""
WS-10 Phase 5.8 ML Promotion Decision Entity definition.
Governs promotion actions, rollback history, and active model inference authority.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    Text,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import AuditEntity


class MLPromotionDecision(AuditEntity):
    """
    SQLAlchemy Entity representing an authoritative model promotion or rollback decision.
    Ensures model promotion is deterministic, explicit, idempotent, and preserves complete rollback capability.
    """
    __tablename__ = "ml_promotion_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    decision_id = Column(String(100), nullable=False, unique=True, index=True)
    evaluation_id = Column(String(100), nullable=False, index=True)
    
    model_family = Column(String(100), nullable=False, index=True)
    previous_promoted_version_id = Column(String(100), nullable=True)
    previous_promoted_version = Column(String(50), nullable=True)
    
    new_promoted_version_id = Column(String(100), nullable=False)
    new_promoted_version = Column(String(50), nullable=False)
    
    decision_type = Column(String(50), nullable=False, server_default="PROMOTED", index=True) # PROMOTED, REJECTED, ROLLED_BACK
    authorized_by = Column(String(100), nullable=False, server_default="AUTHORITATIVE_GOVERNANCE_ENGINE")
    authorization_reason = Column(String(500), nullable=True)
    
    is_active_authority = Column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)
    decision_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_promotion_family_active", "model_family", "is_active_authority"),
    )
