"""
WS-10 Phase 6.3 ML Batch Processing Cursor ORM Entity
Defines persistent high-watermark cursor entity (`ml_batch_processing_cursors`) for incremental batch prediction.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditEntity


class MLBatchProcessingCursor(AuditEntity):
    """
    High-watermark cursor for incremental batch inference processing (`ml_batch_processing_cursors`).
    Tracks last processed dispatch timestamp and ID to prevent redundant inference re-execution.
    """

    __tablename__ = "ml_batch_processing_cursors"

    batch_job_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    last_processed_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_processed_dispatch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_dispatches_processed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
    total_snapshots_generated: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
