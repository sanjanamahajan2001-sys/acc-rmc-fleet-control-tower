import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, UniqueConstraint, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class MLFeedbackRecord(Base):
    """
    Tracks realized operational outcomes matched against prediction snapshots
    for closed-loop feedback and continuous learning evaluation.
    """
    __tablename__ = "ml_feedback_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_id = Column(String(100), unique=True, nullable=False, index=True)
    dispatch_id = Column(String(100), nullable=False, index=True)
    outcome_id = Column(String(100), nullable=False, index=True)
    model_family = Column(String(50), nullable=False, index=True)
    model_version_id = Column(String(100), nullable=False, index=True)
    prediction_snapshot_id = Column(String(100), nullable=False, index=True)
    
    predicted_value = Column(Float, nullable=False)
    realized_value = Column(Float, nullable=False)
    error_delta = Column(Float, nullable=False)
    is_error_outlier = Column(Boolean, default=False, nullable=False)
    
    planner_action_taken = Column(String(100), nullable=True)
    feedback_metadata = Column(JSON, nullable=True)
    feedback_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("prediction_snapshot_id", "outcome_id", name="uq_feedback_snapshot_outcome"),
        Index("idx_feedback_family_ts", "model_family", "feedback_timestamp"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "feedback_id": self.feedback_id,
            "dispatch_id": self.dispatch_id,
            "outcome_id": self.outcome_id,
            "model_family": self.model_family,
            "model_version_id": self.model_version_id,
            "prediction_snapshot_id": self.prediction_snapshot_id,
            "predicted_value": self.predicted_value,
            "realized_value": self.realized_value,
            "error_delta": self.error_delta,
            "is_error_outlier": self.is_error_outlier,
            "planner_action_taken": self.planner_action_taken,
            "feedback_timestamp": self.feedback_timestamp.isoformat() if self.feedback_timestamp else None,
        }
