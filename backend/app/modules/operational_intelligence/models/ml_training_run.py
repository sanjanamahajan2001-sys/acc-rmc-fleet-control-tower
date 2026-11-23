"""
WS-10 Phase 5.6 ML Training Run Entity definition.
Governs candidate model training execution runs, temporal splits, configuration hashing, and candidate registry lineage.
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditEntity


class MLTrainingRun(AuditEntity):
    """
    SQLAlchemy Entity representing an immutable ML training run execution for candidate model generation.
    """
    __tablename__ = "ml_training_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    training_run_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Bound WS5.5 Training Dataset Details
    dataset_id = Column(String(100), nullable=False, index=True)
    dataset_version = Column(String(50), nullable=False, server_default="v1.0.0")
    dataset_content_hash = Column(String(64), nullable=False, index=True)
    model_family = Column(String(100), nullable=False, index=True)
    feature_set_version = Column(String(50), nullable=False, server_default="FeatureSetV1")
    target_name = Column(String(100), nullable=False)
    total_dataset_rows = Column(Integer, nullable=False, default=0)
    
    # Train / Validation / Holdout Temporal Split
    train_row_count = Column(Integer, nullable=False, default=0)
    validation_row_count = Column(Integer, nullable=False, default=0)
    holdout_row_count = Column(Integer, nullable=False, default=0)
    split_strategy = Column(String(50), nullable=False, server_default="TEMPORAL")
    split_boundaries = Column(JSONB, nullable=True)
    
    # Model Training Configuration & Immutable Hash
    algorithm = Column(String(100), nullable=False, server_default="LIGHTGBM")
    hyperparameters = Column(JSONB, nullable=False)
    random_seed = Column(Integer, nullable=False, default=42)
    config_hash = Column(String(64), nullable=False, index=True)
    framework_versions = Column(JSONB, nullable=True)
    python_version = Column(String(50), nullable=False, server_default="3.12")
    training_engine_version = Column(String(50), nullable=False, server_default="v1.0.0-ws5.6")

    # Training Run Lifecycle Status
    run_status = Column(String(50), nullable=False, server_default="TRAINING", index=True) # TRAINING, TRAINED, VALIDATED, CANDIDATE, FAILED
    failure_reason = Column(String(500), nullable=True)
    metrics = Column(JSONB, nullable=True)

    # Candidate Model & Artifact Lineage
    candidate_model_version_id = Column(String(100), nullable=True, index=True)
    artifact_path = Column(String(255), nullable=True)
    artifact_sha256 = Column(String(64), nullable=True)
    artifact_size_bytes = Column(Integer, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("dataset_id", "model_family", "config_hash", name="uq_training_run_identity"),
        Index("idx_training_run_family_status", "model_family", "run_status"),
    )
