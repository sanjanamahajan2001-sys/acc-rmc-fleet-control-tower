import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class ContinuousLearningTrigger(Base):
    """
    Tracks automated retraining triggers when model error thresholds are exceeded.
    """
    __tablename__ = "continuous_learning_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_id = Column(String(100), unique=True, nullable=False, index=True)
    model_family = Column(String(50), nullable=False, index=True)
    current_model_version_id = Column(String(100), nullable=False)
    
    trigger_reason = Column(String(255), nullable=False)
    eval_period_days = Column(Float, default=7.0, nullable=False)
    total_feedback_samples = Column(Float, nullable=False)
    
    error_mae = Column(Float, nullable=True)
    error_rmse = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    
    retrain_recommended = Column(Boolean, default=False, nullable=False)
    trigger_status = Column(String(50), default="PENDING", nullable=False)
    triggered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_trigger_family_status", "model_family", "trigger_status"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "trigger_id": self.trigger_id,
            "model_family": self.model_family,
            "current_model_version_id": self.current_model_version_id,
            "trigger_reason": self.trigger_reason,
            "eval_period_days": self.eval_period_days,
            "total_feedback_samples": self.total_feedback_samples,
            "error_mae": self.error_mae,
            "error_rmse": self.error_rmse,
            "accuracy_score": self.accuracy_score,
            "retrain_recommended": self.retrain_recommended,
            "trigger_status": self.trigger_status,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
        }
