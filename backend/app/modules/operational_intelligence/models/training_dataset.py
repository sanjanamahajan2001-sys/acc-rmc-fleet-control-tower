"""
WS-10 Phase 5.5 Historical Verified Dataset Builder ORM Entities
Governs versioned, immutable, quality-gated training datasets and normalized row lineage.
"""

import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import AuditEntity

class HistoricalTrainingDataset(AuditEntity):
    """
    Historical Training Dataset Entity representing a versioned, quality-validated
    training dataset built strictly from non-superseded verified outcome lineage.
    """
    __tablename__ = "historical_training_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    dataset_id = Column(String(100), nullable=False, unique=True, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    dataset_version = Column(String(50), nullable=False, server_default="v1.0.0")
    model_family = Column(String(100), nullable=False, index=True)
    feature_set_version = Column(String(50), nullable=False, server_default="FeatureSetV1")
    scope_type = Column(String(50), nullable=False, server_default="GLOBAL")
    scope_id = Column(String(100), nullable=True)
    
    # Temporal & Cutoff Boundaries
    source_time_range_start = Column(DateTime(timezone=True), nullable=False)
    source_time_range_end = Column(DateTime(timezone=True), nullable=False)
    generation_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    evaluation_cutoff = Column(DateTime(timezone=True), nullable=False)

    # Counts & Metrics
    total_row_count = Column(Integer, nullable=False, default=0)
    source_outcome_count = Column(Integer, nullable=False, default=0)
    source_error_count = Column(Integer, nullable=False, default=0)
    source_snapshot_count = Column(Integer, nullable=False, default=0)
    
    # Governance & Policies
    validation_policy_version = Column(String(50), nullable=False, server_default="WS55_QUALITY_GATE_V1")
    leakage_policy_version = Column(String(50), nullable=False, server_default="FEATURE_SET_V1_STRICT_NO_LEAKAGE")
    code_version = Column(String(50), nullable=False, server_default="v1.0.0-phase55-dataset-builder")
    dataset_content_hash = Column(String(64), nullable=False, index=True) # SHA-256
    
    # Quality Gate State & Results
    dataset_status = Column(String(50), nullable=False, server_default="GENERATED", index=True) # GENERATED, VALIDATING, READY_FOR_TRAINING, REJECTED, SUPERSEDED
    quality_gate_passed = Column(Boolean, nullable=False, default=False)
    rejection_reason = Column(String(500), nullable=True)
    quality_metrics = Column(JSONB, nullable=True)
    
    # Lineage Summary
    source_record_ids = Column(JSONB, nullable=True) # Summary JSONB capped at 1000 IDs
    
    # Supersession Lineage
    is_superseded = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    superseded_by_dataset_id = Column(String(100), nullable=True)

    # Relationships
    rows = relationship("HistoricalTrainingDatasetRow", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint(
            "model_family",
            "feature_set_version",
            "scope_type",
            "scope_id",
            "dataset_version",
            "source_time_range_start",
            "source_time_range_end",
            "dataset_content_hash",
            name="uq_training_dataset_identity",
        ),
        Index("idx_dataset_family_status", "model_family", "dataset_status"),
    )


class HistoricalTrainingDatasetRow(AuditEntity):
    """
    Normalized row-level lineage entity for historical training dataset rows.
    Provides 100% complete queryable lineage tracing for every individual sample.
    """
    __tablename__ = "historical_training_dataset_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    dataset_id = Column(String(100), ForeignKey("historical_training_datasets.dataset_id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    
    # Explicit Provenance Lineage IDs
    outcome_id = Column(String(100), nullable=False, index=True)
    prediction_error_record_id = Column(String(100), nullable=True, index=True)
    prediction_snapshot_id = Column(String(100), nullable=True, index=True)
    model_version_id = Column(String(100), nullable=False, index=True)
    dispatch_id = Column(String(100), nullable=True)

    # Feature & Label Storage
    features_json = Column(JSONB, nullable=False)
    label_json = Column(JSONB, nullable=False)
    label_numeric = Column(Numeric(14, 4), nullable=True)
    label_class = Column(Integer, nullable=True)
    
    # Financial Exposure & Impact (NULL preserved!)
    realized_financial_impact_inr = Column(Numeric(14, 2), nullable=True)

    # Relationship
    dataset = relationship("HistoricalTrainingDataset", back_populates="rows")

    __table_args__ = (
        UniqueConstraint("dataset_id", "row_index", name="uq_dataset_row_index"),
        Index("idx_dataset_row_outcome", "dataset_id", "outcome_id"),
    )
