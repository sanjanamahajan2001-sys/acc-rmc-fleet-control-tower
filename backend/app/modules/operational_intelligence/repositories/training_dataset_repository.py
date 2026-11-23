"""
WS-10 Phase 5.5 Historical Verified Dataset Builder Repository
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.operational_intelligence.models.training_dataset import (
    HistoricalTrainingDataset,
    HistoricalTrainingDatasetRow,
)

class TrainingDatasetRepository:
    """Repository managing dataset storage and row-level lineage persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dataset_id(self, dataset_id: str) -> Optional[HistoricalTrainingDataset]:
        """Fetch dataset entity by dataset_id."""
        stmt = (
            select(HistoricalTrainingDataset)
            .where(
                HistoricalTrainingDataset.dataset_id == dataset_id,
                HistoricalTrainingDataset.is_deleted == False,
            )
            .options(selectinload(HistoricalTrainingDataset.rows))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[HistoricalTrainingDataset]:
        """Fetch dataset entity by idempotency key."""
        stmt = (
            select(HistoricalTrainingDataset)
            .where(
                HistoricalTrainingDataset.idempotency_key == idempotency_key,
                HistoricalTrainingDataset.is_superseded == False,
                HistoricalTrainingDataset.is_deleted == False,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_dataset(
        self,
        model_family: str,
        feature_set_version: str = "FeatureSetV1",
        scope_type: str = "GLOBAL",
        scope_id: Optional[str] = None,
    ) -> Optional[HistoricalTrainingDataset]:
        """Fetch latest active READY_FOR_TRAINING dataset."""
        stmt = (
            select(HistoricalTrainingDataset)
            .where(
                HistoricalTrainingDataset.model_family == model_family,
                HistoricalTrainingDataset.feature_set_version == feature_set_version,
                HistoricalTrainingDataset.scope_type == scope_type,
                HistoricalTrainingDataset.dataset_status == "READY_FOR_TRAINING",
                HistoricalTrainingDataset.is_superseded == False,
                HistoricalTrainingDataset.is_deleted == False,
            )
        )
        if scope_id:
            stmt = stmt.where(HistoricalTrainingDataset.scope_id == scope_id)
        stmt = stmt.order_by(HistoricalTrainingDataset.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dataset_rows(self, dataset_id: str, limit: int = 1000, offset: int = 0) -> List[HistoricalTrainingDatasetRow]:
        """Fetch normalized row lineage for a dataset."""
        stmt = (
            select(HistoricalTrainingDatasetRow)
            .where(
                HistoricalTrainingDatasetRow.dataset_id == dataset_id,
                HistoricalTrainingDatasetRow.is_deleted == False,
            )
            .order_by(HistoricalTrainingDatasetRow.row_index.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def persist_dataset_with_rows(
        self,
        dataset: HistoricalTrainingDataset,
        rows: List[HistoricalTrainingDatasetRow],
    ) -> HistoricalTrainingDataset:
        """Atomically persist dataset metadata and all normalized row lineage entries."""
        self.session.add(dataset)
        await self.session.flush()
        
        for r in rows:
            r.dataset_id = dataset.dataset_id
            self.session.add(r)
            
        await self.session.commit()
        await self.session.refresh(dataset)
        return dataset
