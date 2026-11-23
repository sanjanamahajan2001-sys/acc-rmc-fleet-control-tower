"""
WS-06.8 Snapshot Security, Integrity & Stale-Plan Protection Engine.
Provides server-authoritative snapshot validation, hash verification, stale detection,
and ERP import/reset invalidation management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationFilterParamsDTO,
    OptimizationSnapshotMetadataDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import (
    DispatchOptimizationSolverEngine,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import (
    DispatchAnalysisRepository,
)


class SnapshotSecurityEngine:
    """Authoritative Snapshot Security, Hash Verification & Stale Detection Engine."""

    @classmethod
    async def evaluate_snapshot_stale_status(
        cls,
        session: AsyncSession,
        stored_snapshot_hash: str,
        filters: OptimizationFilterParamsDTO,
    ) -> Dict[str, Any]:
        """
        Queries current PostgreSQL database state and compares current SHA-256 fingerprint hash
        against stored_snapshot_hash.
        Returns:
            {
                "is_stale": bool,
                "stored_hash": str,
                "current_hash": str,
                "reason": str
            }
        """
        # Fetch current dispatches from PostgreSQL using exact filter scope via get_scoped_dispatches
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(
            session, filters.model_dump()
        )

        current_hash = DispatchOptimizationSolverEngine.compute_canonical_snapshot_hash(
            dispatches, filters
        )

        is_stale = stored_snapshot_hash != current_hash

        reason = "CURRENT_SNAPSHOT_VALID"
        if is_stale:
            reason = "STALE_SNAPSHOT_ERP_DATASET_MUTATED"

        return {
            "is_stale": is_stale,
            "stored_hash": stored_snapshot_hash,
            "current_hash": current_hash,
            "reason": reason,
        }

    @classmethod
    def validate_snapshot_hash_format(cls, snapshot_hash: str) -> bool:
        """Validates that a snapshot hash is a valid 64-character SHA-256 hex string."""
        if not snapshot_hash or not isinstance(snapshot_hash, str):
            return False
        if len(snapshot_hash) != 64:
            return False
        try:
            int(snapshot_hash, 16)
            return True
        except ValueError:
            return False
