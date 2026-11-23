"""
WS-10 Phase 5.8 ML Evaluation Record Entity definition.
Governs candidate model evaluation execution on holdout sets, model-family metrics, calibration scores, and gate results.
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


class MLEvaluationRecord(AuditEntity):
    """
    SQLAlchemy Entity representing an immutable ML model evaluation record.
    Binds holdout set evaluation results, dataset content hashes, artifact SHA-256 signatures, and gate metrics.
    """
    __tablename__ = "ml_evaluation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    evaluation_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Model Version & Candidate Identification
    candidate_model_version_id = Column(String(100), nullable=False, index=True)
    candidate_version = Column(String(50), nullable=False)
    model_family = Column(String(100), nullable=False, index=True)
    
    # Bound WS5.5 Training Dataset Identification & Cryptographic Lineage
    dataset_id = Column(String(100), nullable=False, index=True)
    dataset_version = Column(String(50), nullable=False, server_default="v1.0.0")
    dataset_content_hash = Column(String(64), nullable=False, index=True)
    artifact_sha256 = Column(String(64), nullable=False)
    config_hash = Column(String(64), nullable=False, index=True)
    
    # Holdout Evaluation Metrics & Multi-Class Semantics (0=NORMAL, 1=MODERATE, 2=SEVERE)
    holdout_sample_count = Column(Integer, nullable=False, default=0)
    evaluation_status = Column(String(50), nullable=False, server_default="EVALUATED", index=True) # EVALUATED, PASSED, FAILED, INSUFFICIENT_DATA, REJECTED
    promotion_recommendation = Column(String(50), nullable=False, server_default="RETAIN_CANDIDATE") # PROMOTE, REJECT, RETAIN_CANDIDATE
    
    # Detailed Metric Payloads & Gate Governance
    metrics = Column(JSONB, nullable=False) # mae, rmse, r2, accuracy, precision, recall, f1, log_loss, calibration_score, multi_class_confusion_matrix
    gate_results = Column(JSONB, nullable=False) # Detailed evaluation gate checks
    rejection_reason = Column(String(500), nullable=True)
    
    # Governance Authority & Timestamps
    evaluator_version = Column(String(50), nullable=False, server_default="v1.0.0-ws5.8")
    evaluation_policy_version = Column(String(50), nullable=False, server_default="WS58_PROMOTION_GATE_V1")
    evaluated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("candidate_model_version_id", "dataset_id", "config_hash", name="uq_evaluation_identity"),
        Index("idx_evaluation_family_status", "model_family", "evaluation_status"),
    )
