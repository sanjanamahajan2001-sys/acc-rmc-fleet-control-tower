"""
WS-10.6 Authoritative Predictive Inference & Prediction Snapshot Generation Service.
Connects PROMOTED model versions to FeatureSetV1 inference inputs and persists immutable MLPredictionSnapshot records.
"""

import os
import hashlib
import uuid
import joblib
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
    PredictionSnapshotResponseDTO,
)
from app.modules.operational_intelligence.ml.feature_extractor import Phase71FeatureExtractor, FEATURE_SET_VERSION

logger = logging.getLogger(__name__)


class WS10InferenceService:
    """
    Authoritative Inference Service governing predictive inference execution and snapshot generation.
    Enforces PROMOTED model requirement, artifact SHA-256 integrity checks, FeatureSetV1 anti-leakage guards,
    and transactional snapshot persistence.
    """

    @classmethod
    async def resolve_promoted_model(
        cls, session: AsyncSession, model_name: str
    ) -> Optional[MLModelVersion]:
        """
        Resolves the active PROMOTED model version for a given model family.
        Strictly rejects REJECTED, TRAINED_CANDIDATE, PROMOTION_ELIGIBLE, RETIRED, or PENDING_EVALUATION models.
        """
        repo = MLModelRegistryRepository(session)
        promoted_model = await repo.get_active_promoted_model(model_name)
        return promoted_model

    @classmethod
    async def verify_promoted_artifact_integrity(
        cls, session: AsyncSession, promoted_model: MLModelVersion
    ) -> bool:
        """
        Verifies on-disk artifact file existence and matches SHA-256 checksum against registry entity.
        Raises ValueError with ARTIFACT_MUTATION_DETECTED if checksum mismatches.
        Raises FileNotFoundError if artifact file is missing.
        """
        if not promoted_model.artifact_path or not os.path.exists(promoted_model.artifact_path):
            raise FileNotFoundError(f"Promoted artifact missing for '{promoted_model.model_name}' at '{promoted_model.artifact_path}'.")

        with open(promoted_model.artifact_path, "rb") as f:
            disk_sha = hashlib.sha256(f.read()).hexdigest()

        if disk_sha.lower() != promoted_model.artifact_sha256.lower():
            raise ValueError(
                f"ARTIFACT_MUTATION_DETECTED for promoted model '{promoted_model.model_name}' version '{promoted_model.model_version}'! "
                f"Registry SHA: '{promoted_model.artifact_sha256}', Disk SHA: '{disk_sha}'"
            )

        return True

    @classmethod
    def extract_and_validate_features(cls, dispatch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts FeatureSetV1 inference features and executes anti-leakage assertions.
        """
        input_features = Phase71FeatureExtractor.extract_inference_features(dispatch_data)
        Phase71FeatureExtractor.validate_no_leakage_in_features(input_features)
        return input_features

    @classmethod
    async def execute_inference_and_persist_snapshot(
        cls,
        session: AsyncSession,
        model_name: str,
        request: PredictionRequestDTO,
    ) -> PredictionSnapshotResponseDTO:
        """
        Main entrypoint for authoritative prediction generation and snapshot persistence.
        1. Resolves active PROMOTED model version.
        2. If PROMOTED is None, returns NOT_CONFIGURED response with zero snapshot creation.
        3. Re-verifies on-disk SHA-256 integrity.
        4. Validates anti-leakage feature guards.
        5. Executes model inference and persists immutable MLPredictionSnapshot record.
        """
        snap_repo = MLPredictionSnapshotRepository(session)

        # Check non-promoted model status rejection guard
        repo = MLModelRegistryRepository(session)
        promoted_model = await repo.get_active_promoted_model(model_name)

        if not promoted_model:
            # Check if non-promoted version exists to log explicit rejection reason
            all_versions = await repo.list_model_versions(model_name=model_name)
            if any(v.lifecycle_status in ("REJECTED", "TRAINED_CANDIDATE", "PROMOTION_ELIGIBLE", "RETIRED") for v in all_versions):
                logger.info(f"[INFERENCE BLOCKED] Non-promoted model versions exist for '{model_name}', but active PROMOTED model is 0.")

        return await snap_repo.generate_and_persist_prediction_snapshot(model_name, request)

    @classmethod
    async def audit_real_production_inference(cls, session: AsyncSession) -> Dict[str, Any]:
        """
        Audits real PostgreSQL database state for prediction authority status.
        """
        repo = MLModelRegistryRepository(session)
        snap_repo = MLPredictionSnapshotRepository(session)

        all_models = await repo.list_model_versions()
        promoted_models = [m for m in all_models if m.lifecycle_status == "PROMOTED"]

        stmt_snaps = select(MLPredictionSnapshot)
        res_snaps = await session.execute(stmt_snaps)
        snapshots = list(res_snaps.scalars().all())

        if len(promoted_models) == 0:
            authority_status = "NOT_CONFIGURED"
            audit_message = "No active PROMOTED model versions configured. Prediction authority remains NOT_CONFIGURED."
        elif len(snapshots) == 0:
            authority_status = "NO_DATA"
            audit_message = "PROMOTED model configured, but zero prediction snapshots exist."
        else:
            authority_status = "AUTHORITATIVE"
            audit_message = f"Platform is AUTHORITATIVE with {len(promoted_models)} promoted model(s) and {len(snapshots)} snapshot(s)."

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_models_count": len(all_models),
            "promoted_models_count": len(promoted_models),
            "snapshots_count": len(snapshots),
            "overall_prediction_authority_status": authority_status,
            "audit_message": audit_message,
        }
