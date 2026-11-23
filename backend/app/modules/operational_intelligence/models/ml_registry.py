"""
WS-09 Phase 7.4 Model Registry & Audit Event ORM Entities

Defines the PostgreSQL ORM entity mapping for:
1. MLModelVersion (`ml_model_versions`)
2. MLModelAuditEvent (`ml_model_audit_events`)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditEntity, BaseEntity


class MLModelVersion(AuditEntity):
    """
    Authoritative ML Model Version & Provenance Entity (`ml_model_versions`).
    Tracks immutable candidate artifacts, evaluation provenance, SHA-256 hashes, and lifecycle state.
    """

    __tablename__ = "ml_model_versions"

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_category: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    training_dataset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    validation_dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    holdout_dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    training_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    promotion_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retirement_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    lifecycle_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="TRAINED_CANDIDATE", server_default=text("'TRAINED_CANDIDATE'"), index=True
    )
    evaluation_decision: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING_EVALUATION", server_default=text("'PENDING_EVALUATION'")
    )
    rejection_reasons: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    hyperparameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42, server_default=text("42"))
    row_counts: Mapped[Optional[Dict[str, int]]] = mapped_column(JSONB, nullable=True)
    evaluation_provenance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships
    audit_events: Mapped[List["MLModelAuditEvent"]] = relationship(
        "MLModelAuditEvent", back_populates="model_version_ref", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="uq_ml_model_versions_name_version"),
        UniqueConstraint(
            "model_name", "feature_set_version", "target_name", "model_version", name="uq_ml_model_versions_identity"
        ),
        Index(
            "uq_active_promoted_model_per_name",
            "model_name",
            unique=True,
            postgresql_where=text("lifecycle_status = 'PROMOTED' AND is_deleted = false"),
        ),
    )


class MLModelAuditEvent(BaseEntity):
    """
    Authoritative ML Model Lifecycle Audit Event Log (`ml_model_audit_events`).
    Tracks state transitions: MODEL_REGISTERED, MODEL_EVALUATED, MODEL_REJECTED, MODEL_PROMOTED, MODEL_RETIRED.
    """

    __tablename__ = "ml_model_audit_events"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False
    )

    model_version_ref: Mapped[MLModelVersion] = relationship("MLModelVersion", back_populates="audit_events")
