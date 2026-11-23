"""
WS-09 Phase 7.4 Model Registry Repository Implementation

Encapsulates database access for MLModelVersion and MLModelAuditEvent.
Provides methods for:
- Candidate model registration with SHA-256 verification
- Model lookup by ID, name, version, or SHA-256
- Active promoted model resolution (strictly returning PROMOTED or NOT_CONFIGURED)
- Evaluation decision persistence
- Transactional promotion & retirement transitions
- Comprehensive audit trail creation
- Artifact verification and integrity checking
"""

import os
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecordNotFoundError
from app.repositories.base import GenericRepository
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent


class MLModelRegistryRepository(GenericRepository[MLModelVersion]):
    """
    Authoritative Repository for ML Model Registry and Version Governance.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(MLModelVersion, session)

    @classmethod
    def _parse_datetime(cls, val: Union[datetime, str, None]) -> Optional[datetime]:
        """Converts ISO string to Python datetime instance if needed."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return None

    async def register_candidate_version(
        self,
        model_name: str,
        model_category: str,
        version_number: str,
        artifact_location: str,
        artifact_sha256: str,
        training_metadata: Dict[str, Any],
        dataset_version: str = "FeatureSetV1",
        created_by: Optional[str] = None,
    ) -> MLModelVersion:
        """
        Registers a new model version entry in ml_model_versions in TRAINED_CANDIDATE state.
        Verifies artifact file exists and SHA-256 matches provided checksum before persisting.
        """
        if not os.path.exists(artifact_location):
            raise FileNotFoundError(f"Artifact file not found at location: '{artifact_location}'")

        with open(artifact_location, "rb") as f:
            computed_sha = hashlib.sha256(f.read()).hexdigest()

        if computed_sha.lower() != artifact_sha256.lower():
            raise ValueError(
                f"Artifact SHA-256 mismatch! Provided: '{artifact_sha256}', Computed: '{computed_sha}'"
            )

        # Check existing version
        stmt = select(MLModelVersion).where(
            and_(
                MLModelVersion.model_name == model_name,
                MLModelVersion.model_version == version_number,
            )
        )
        res = await self.session.execute(stmt)
        existing = res.scalars().first()
        if existing:
            if existing.artifact_sha256.lower() != computed_sha.lower():
                raise ValueError(
                    f"ARTIFACT MUTATION DETECTED for '{model_name}' version '{version_number}'! "
                    f"Registered SHA-256: '{existing.artifact_sha256}', On-disk SHA-256: '{computed_sha}'"
                )
            return existing

        now = datetime.now(timezone.utc)
        model_version = MLModelVersion(
            model_name=model_name,
            model_category=model_category,
            model_version=version_number,
            algorithm=training_metadata.get("algorithm", "RandomForest"),
            target_name=training_metadata.get("target_name", "target"),
            feature_set_version=dataset_version,
            training_dataset_id=training_metadata.get("training_dataset_id", "DS-UNKNOWN"),
            artifact_path=artifact_location,
            artifact_sha256=computed_sha,
            artifact_size_bytes=os.path.getsize(artifact_location),
            training_timestamp=now,
            lifecycle_status="TRAINED_CANDIDATE",
            evaluation_decision="PENDING_EVALUATION",
            hyperparameters=training_metadata.get("hyperparameters", {}),
            random_seed=training_metadata.get("random_seed", 42),
            row_counts={
                "train": training_metadata.get("train_row_count", 0),
                "validation": training_metadata.get("val_row_count", 0),
                "holdout": training_metadata.get("holdout_row_count", 0),
            },
            evaluation_provenance=training_metadata,
            created_at=now,
            updated_at=now,
        )
        self.session.add(model_version)
        await self.session.flush()

        audit = MLModelAuditEvent(
            model_version_id=model_version.id,
            model_name=model_name,
            model_version=version_number,
            event_type="MODEL_REGISTERED",
            previous_status=None,
            new_status="TRAINED_CANDIDATE",
            artifact_sha256=computed_sha,
            decision_details={"reason": f"Candidate model version {version_number} registered successfully", "dataset_version": dataset_version},
            event_timestamp=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(audit)
        return model_version

    async def verify_registered_artifact_sha(self, model_name: str, version_number: str) -> bool:
        """
        Verifies on-disk artifact SHA-256 against stored database SHA-256.
        Returns True if matched.
        Raises ValueError with ARTIFACT MUTATION DETECTED if artifact has been modified or corrupted.
        Raises FileNotFoundError if artifact file is missing.
        """
        version_entity = await self.get_by_version_number(model_name, version_number)
        if not version_entity:
            raise RecordNotFoundError(f"Model version '{version_number}' for '{model_name}' not found.")

        art_path = version_entity.artifact_path
        if not os.path.exists(art_path):
            raise FileNotFoundError(f"Artifact file missing for '{model_name}' ({version_number}) at '{art_path}'.")

        with open(art_path, "rb") as f:
            disk_sha = hashlib.sha256(f.read()).hexdigest()

        if disk_sha.lower() != version_entity.artifact_sha256.lower():
            raise ValueError(
                f"ARTIFACT MUTATION DETECTED for '{model_name}' version '{version_number}'! "
                f"Registered SHA: '{version_entity.artifact_sha256}', Disk SHA: '{disk_sha}'"
            )

        return True

    async def get_by_version_number(self, model_name: str, version_number: str) -> Optional[MLModelVersion]:
        stmt = select(MLModelVersion).where(
            and_(
                MLModelVersion.model_name == model_name,
                MLModelVersion.model_version == version_number,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_model_versions(self, model_name: Optional[str] = None) -> List[MLModelVersion]:
        stmt = select(MLModelVersion).order_by(MLModelVersion.created_at.desc())
        if model_name:
            stmt = stmt.where(MLModelVersion.model_name == model_name)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_active_promoted_model(self, model_name: str) -> Optional[MLModelVersion]:
        stmt = select(MLModelVersion).where(
            and_(
                MLModelVersion.model_name == model_name,
                MLModelVersion.lifecycle_status == "PROMOTED",
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_pending_evaluation_candidates(
        self, model_name: Optional[str] = None
    ) -> List[MLModelVersion]:
        """
        Returns all candidate model versions with lifecycle_status='TRAINED_CANDIDATE'
        and evaluation_decision='PENDING_EVALUATION'.
        """
        stmt = select(MLModelVersion).where(
            and_(
                MLModelVersion.lifecycle_status == "TRAINED_CANDIDATE",
                MLModelVersion.evaluation_decision == "PENDING_EVALUATION",
            )
        )
        if model_name:
            stmt = stmt.where(MLModelVersion.model_name == model_name)
        stmt = stmt.order_by(MLModelVersion.created_at.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def claim_next_pending_candidate(
        self, model_name: Optional[str] = None
    ) -> Optional[MLModelVersion]:
        """
        Claims the next pending candidate model using SELECT FOR UPDATE SKIP LOCKED
        to guarantee concurrent worker safety.
        """
        stmt = (
            select(MLModelVersion)
            .where(
                and_(
                    MLModelVersion.lifecycle_status == "TRAINED_CANDIDATE",
                    MLModelVersion.evaluation_decision == "PENDING_EVALUATION",
                )
            )
            .with_for_update(skip_locked=True)
            .order_by(MLModelVersion.created_at.asc())
        )
        if model_name:
            stmt = stmt.where(MLModelVersion.model_name == model_name)
        res = await self.session.execute(stmt)
        candidate = res.scalars().first()
        if candidate:
            candidate.evaluation_decision = "EVALUATING"
            candidate.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
        return candidate

    async def update_evaluation_decision(
        self,
        version_id: uuid.UUID,
        new_decision: str,
        new_lifecycle_status: str,
        rejection_reasons: Optional[List[str]] = None,
        evaluation_provenance: Optional[Dict[str, Any]] = None,
    ) -> MLModelVersion:
        """
        Persists evaluation decision, updates status, and appends audit event.
        """
        stmt = select(MLModelVersion).where(MLModelVersion.id == version_id)
        res = await self.session.execute(stmt)
        version_entity = res.scalars().first()
        if not version_entity:
            raise RecordNotFoundError(f"Model version with id '{version_id}' not found.")

        prev_status = version_entity.lifecycle_status
        now = datetime.now(timezone.utc)
        version_entity.evaluation_decision = new_decision
        version_entity.lifecycle_status = new_lifecycle_status
        version_entity.evaluation_timestamp = now
        version_entity.updated_at = now
        if rejection_reasons is not None:
            version_entity.rejection_reasons = rejection_reasons
        if evaluation_provenance is not None:
            if version_entity.evaluation_provenance:
                prov = dict(version_entity.evaluation_provenance)
                prov.update(evaluation_provenance)
                version_entity.evaluation_provenance = prov
            else:
                version_entity.evaluation_provenance = evaluation_provenance

        audit_event_type = "MODEL_EVALUATED" if new_decision in ("PROMOTION_ELIGIBLE", "EVALUATION_PASSED", "PROMOTABLE") else "MODEL_REJECTED"
        audit = MLModelAuditEvent(
            model_version_id=version_entity.id,
            model_name=version_entity.model_name,
            model_version=version_entity.model_version,
            event_type=audit_event_type,
            previous_status=prev_status,
            new_status=new_lifecycle_status,
            artifact_sha256=version_entity.artifact_sha256,
            decision_details={
                "evaluation_decision": new_decision,
                "rejection_reasons": rejection_reasons or [],
                "provenance": evaluation_provenance or {},
            },
            event_timestamp=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(audit)
        await self.session.flush()
        return version_entity

    async def get_promotion_eligible_candidates(
        self, model_name: Optional[str] = None
    ) -> List[MLModelVersion]:
        """
        Returns all candidate model versions with lifecycle_status='TRAINED_CANDIDATE'
        and evaluation_decision='PROMOTION_ELIGIBLE'.
        """
        stmt = select(MLModelVersion).where(
            and_(
                MLModelVersion.lifecycle_status == "TRAINED_CANDIDATE",
                MLModelVersion.evaluation_decision == "PROMOTION_ELIGIBLE",
            )
        )
        if model_name:
            stmt = stmt.where(MLModelVersion.model_name == model_name)
        stmt = stmt.order_by(MLModelVersion.evaluation_timestamp.desc(), MLModelVersion.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def promote_candidate_model_version(
        self,
        version_id: uuid.UUID,
        promoter_info: Optional[Dict[str, Any]] = None,
        replacement_policy: str = "REJECT_IF_PROMOTED_EXISTS",
    ) -> MLModelVersion:
        """
        Safely promotes a candidate model version to PROMOTED status.
        Enforces:
        - Candidate must exist, have lifecycle_status='TRAINED_CANDIDATE' and evaluation_decision='PROMOTION_ELIGIBLE'.
        - On-disk artifact SHA-256 integrity verification.
        - Single active promoted model per family constraint (handles replacement or raises ValueError).
        - Atomic state update with promotion_timestamp and MLModelAuditEvent ('MODEL_PROMOTED').
        """
        stmt = select(MLModelVersion).where(MLModelVersion.id == version_id).with_for_update()
        res = await self.session.execute(stmt)
        version_entity = res.scalars().first()
        if not version_entity:
            raise RecordNotFoundError(f"Model version with id '{version_id}' not found.")

        if version_entity.lifecycle_status == "REJECTED":
            raise ValueError(f"Cannot promote model '{version_entity.model_name}' version '{version_entity.model_version}': Candidate is REJECTED.")

        if version_entity.lifecycle_status == "RETIRED":
            raise ValueError(f"Cannot promote model '{version_entity.model_name}' version '{version_entity.model_version}': Candidate is RETIRED.")

        if version_entity.lifecycle_status == "PROMOTED":
            raise ValueError(f"Candidate model '{version_entity.model_name}' version '{version_entity.model_version}' is ALREADY PROMOTED.")

        if version_entity.lifecycle_status != "TRAINED_CANDIDATE" or version_entity.evaluation_decision != "PROMOTION_ELIGIBLE":
            raise ValueError(
                f"Candidate model '{version_entity.model_name}' version '{version_entity.model_version}' "
                f"is not eligible for promotion (status: '{version_entity.lifecycle_status}', decision: '{version_entity.evaluation_decision}')."
            )

        # Verify artifact SHA-256 on disk
        await self.verify_registered_artifact_sha(version_entity.model_name, version_entity.model_version)

        # Check existing active promoted model for this family
        active_promoted = await self.get_active_promoted_model(version_entity.model_name)
        if active_promoted and active_promoted.id != version_entity.id:
            if replacement_policy == "REJECT_IF_PROMOTED_EXISTS":
                raise ValueError(
                    f"Promotion blocked: An active promoted model version '{active_promoted.model_version}' "
                    f"already exists for model family '{version_entity.model_name}'."
                )
            elif replacement_policy == "RETIRE_EXISTING":
                now_retire = datetime.now(timezone.utc)
                active_promoted.lifecycle_status = "RETIRED"
                active_promoted.updated_at = now_retire
                audit_retire = MLModelAuditEvent(
                    model_version_id=active_promoted.id,
                    model_name=active_promoted.model_name,
                    model_version=active_promoted.model_version,
                    event_type="MODEL_RETIRED",
                    previous_status="PROMOTED",
                    new_status="RETIRED",
                    artifact_sha256=active_promoted.artifact_sha256,
                    decision_details={"reason": f"Replaced by newly promoted version '{version_entity.model_version}'"},
                    event_timestamp=now_retire,
                    created_at=now_retire,
                    updated_at=now_retire,
                )
                self.session.add(audit_retire)

        prev_status = version_entity.lifecycle_status
        now = datetime.now(timezone.utc)

        version_entity.lifecycle_status = "PROMOTED"
        version_entity.promotion_timestamp = now
        version_entity.updated_at = now

        promoter_details = promoter_info or {"actor": "WS-10.5 Promotion System", "source": "WS10ModelPromotionService"}
        audit = MLModelAuditEvent(
            model_version_id=version_entity.id,
            model_name=version_entity.model_name,
            model_version=version_entity.model_version,
            event_type="MODEL_PROMOTED",
            previous_status=prev_status,
            new_status="PROMOTED",
            artifact_sha256=version_entity.artifact_sha256,
            decision_details={
                "promotion_timestamp": now.isoformat(),
                "promoter_info": promoter_details,
                "dataset_id": version_entity.training_dataset_id,
                "feature_set_version": version_entity.feature_set_version,
            },
            event_timestamp=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(audit)
        await self.session.flush()
        return version_entity

