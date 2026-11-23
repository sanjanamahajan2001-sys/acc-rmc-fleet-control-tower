"""
WS-10 Phase 5.4 Model Health Repository (`model_health_repository.py`).
Provides atomic data access for ModelHealthMetric and ModelHealthMetricSource entities.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.model_health import ModelHealthMetric, ModelHealthMetricSource

logger = logging.getLogger(__name__)


class ModelHealthRepository:
    """Repository managing ModelHealthMetric and ModelHealthMetricSource persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, health_record_id: str) -> Optional[ModelHealthMetric]:
        """Fetch active health metric record by ID."""
        stmt = select(ModelHealthMetric).where(
            ModelHealthMetric.health_record_id == health_record_id,
            ModelHealthMetric.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ModelHealthMetric]:
        """Fetch active health metric record by idempotency key."""
        stmt = select(ModelHealthMetric).where(
            ModelHealthMetric.idempotency_key == idempotency_key,
            ModelHealthMetric.is_superseded == False,
            ModelHealthMetric.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_latest_health(
        self,
        model_name: str,
        model_version_id: Optional[str] = None,
        scope_type: str = "GLOBAL",
        scope_id: Optional[str] = None,
        window_type: str = "30d",
    ) -> Optional[ModelHealthMetric]:
        """Fetch latest active health metric record matching model/version/scope/window criteria."""
        stmt = select(ModelHealthMetric).where(
            ModelHealthMetric.model_name == model_name,
            ModelHealthMetric.scope_type == scope_type,
            ModelHealthMetric.window_type == window_type,
            ModelHealthMetric.is_superseded == False,
            ModelHealthMetric.is_deleted == False,
        )

        if model_version_id:
            stmt = stmt.where(
                or_(
                    ModelHealthMetric.model_version_id == model_version_id,
                    ModelHealthMetric.model_version == model_version_id,
                )
            )

        if scope_id:
            stmt = stmt.where(ModelHealthMetric.scope_id == scope_id)
        else:
            stmt = stmt.where(ModelHealthMetric.scope_id == None)

        stmt = stmt.order_by(ModelHealthMetric.evaluation_timestamp.desc(), ModelHealthMetric.created_at.desc())
        return (await self.session.execute(stmt)).scalars().first()

    async def persist_health_with_sources(
        self,
        health_metric: ModelHealthMetric,
        source_error_record_ids: List[str],
    ) -> ModelHealthMetric:
        """Atomically persists health metric record and associated normalized source lineage records."""
        self.session.add(health_metric)
        await self.session.flush()

        # Insert 100% complete normalized source lineage records
        for err_id in source_error_record_ids:
            source_ref = ModelHealthMetricSource(
                health_record_id=health_metric.health_record_id,
                prediction_error_record_id=err_id,
            )
            self.session.add(source_ref)

        await self.session.commit()
        return health_metric

    async def get_sources_for_health_record(self, health_record_id: str) -> List[str]:
        """Fetch all 100% complete normalized prediction error record IDs for a given health record."""
        stmt = select(ModelHealthMetricSource.prediction_error_record_id).where(
            ModelHealthMetricSource.health_record_id == health_record_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
