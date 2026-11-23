from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text 
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base

class ReportExecutionAudit(Base):
    __tablename__ = "tbl_report_execution_audit"



    execution_id = Column(String(100), primary_key=True, index=True)
    report_id = Column(String(100), nullable=False, index=True)
    report_type = Column(String(100), nullable=False, index=True)
    format = Column(String(20), nullable=False)
    requested_by = Column(String(100), nullable=False, index=True, default="SYSTEM")
    requested_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    requested_scope = Column(JSONB, nullable=False)
    effective_scope = Column(JSONB, nullable=False)
    scope_fingerprint = Column(String(100), nullable=False, index=True)
    scope_validation_status = Column(String(50), nullable=False)
    record_count = Column(Integer, nullable=False, default=0)
    dataset_id = Column(String(100), nullable=True, index=True)
    status = Column(String(50), nullable=False, index=True, default="QUEUED")
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    artifact_path = Column(Text, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    retention_expires_at = Column(DateTime(timezone=True), nullable=True)
