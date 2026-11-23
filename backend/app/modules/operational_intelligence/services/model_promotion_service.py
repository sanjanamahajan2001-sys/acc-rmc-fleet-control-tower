"""
WS-10 Phase 5.8 Model Promotion Governance Service
Governs promotion authorization, model lifecycle state transitions, atomic database updates, and rollback capability.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.ml_evaluation_record import MLEvaluationRecord
from app.modules.operational_intelligence.models.ml_promotion_decision import MLPromotionDecision

logger = logging.getLogger(__name__)


class ModelPromotionService:
    """
    Authoritative Governance Service for Model Promotion & Rollback.
    Enforces explicit promotion authorization, holdout evaluation verification, atomic authority switching, and rollback capabilities.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def promote_candidate_model(
        self,
        candidate_model_version_id: str,
        authorized_by: str = "AUTHORITATIVE_GOVERNANCE_ENGINE",
        authorization_reason: Optional[str] = "Passed WS5.8 holdout performance gates.",
    ) -> MLPromotionDecision:
        """
        Executes atomic promotion of candidate model to PROMOTED status:
        1. Verify candidate evaluation record exists and status is PASSED.
        2. Prevent rejected or un-evaluated candidates from becoming active inference authority.
        3. Fetch current active PROMOTED version for model family.
        4. Atomically set current PROMOTED version to SUPERSEDED.
        5. Set candidate model lifecycle_status to PROMOTED.
        6. Persist MLPromotionDecision record.
        """
        # 1. Fetch Candidate Model Version
        stmt_cand = select(MLModelVersion).where(MLModelVersion.id == candidate_model_version_id)
        res_cand = await self.session.execute(stmt_cand)
        cand_model = res_cand.scalar_one_or_none()

        if not cand_model:
            raise ValueError(f"Candidate model version '{candidate_model_version_id}' not found.")

        # 2. Verify Passed Evaluation Record
        stmt_eval = select(MLEvaluationRecord).where(
            MLEvaluationRecord.candidate_model_version_id == str(cand_model.id),
            MLEvaluationRecord.evaluation_status == "PASSED",
        )
        res_eval = await self.session.execute(stmt_eval)
        eval_record = res_eval.scalars().first()

        if not eval_record:
            raise ValueError(f"Candidate model '{cand_model.id}' has no PASSED evaluation record. Cannot promote unverified or rejected model.")

        model_family = cand_model.model_name

        # 3. Fetch Current Active Promoted Model Version
        stmt_curr = select(MLModelVersion).where(
            MLModelVersion.model_name == model_family,
            MLModelVersion.lifecycle_status == "PROMOTED",
            MLModelVersion.is_deleted == False,
        )
        res_curr = await self.session.execute(stmt_curr)
        prev_promoted = res_curr.scalar_one_or_none()

        prev_id = str(prev_promoted.id) if prev_promoted else None
        prev_ver = prev_promoted.model_version if prev_promoted else None

        # 4. Demote Previous Promoted Model to SUPERSEDED
        if prev_promoted:
            prev_promoted.lifecycle_status = "SUPERSEDED"
            await self.session.flush()

        # 5. Promote Candidate Model
        cand_model.lifecycle_status = "PROMOTED"
        cand_model.promotion_timestamp = datetime.now(timezone.utc)

        # De-activate previous promotion decision records
        await self.session.execute(
            update(MLPromotionDecision)
            .where(MLPromotionDecision.model_family == model_family)
            .values(is_active_authority=False)
        )

        # 6. Create Active Promotion Decision Record
        decision = MLPromotionDecision(
            decision_id=f"PROM-{model_family[:6].upper()}-{uuid.uuid4().hex[:6]}",
            evaluation_id=eval_record.evaluation_id,
            model_family=model_family,
            previous_promoted_version_id=prev_id,
            previous_promoted_version=prev_ver,
            new_promoted_version_id=str(cand_model.id),
            new_promoted_version=cand_model.model_version,
            decision_type="PROMOTED",
            authorized_by=authorized_by,
            authorization_reason=authorization_reason,
            is_active_authority=True,
            decision_timestamp=datetime.now(timezone.utc),
        )

        self.session.add(decision)
        await self.session.commit()
        logger.info(f"MODEL PROMOTED: {model_family} -> {cand_model.model_version} (Authorized by: {authorized_by})")
        return decision

    async def rollback_promoted_model(
        self,
        model_family: str,
        authorized_by: str = "AUTHORITATIVE_GOVERNANCE_ENGINE",
        rollback_reason: Optional[str] = "Manual rollback triggered due to performance anomaly.",
    ) -> MLPromotionDecision:
        """
        Executes atomic rollback of current PROMOTED model to previous SUPERSEDED model version.
        """
        # Fetch current active decision
        stmt_dec = select(MLPromotionDecision).where(
            MLPromotionDecision.model_family == model_family,
            MLPromotionDecision.is_active_authority == True,
        )
        res_dec = await self.session.execute(stmt_dec)
        active_dec = res_dec.scalar_one_or_none()

        if not active_dec or not active_dec.previous_promoted_version_id:
            raise ValueError(f"No previous promoted version available for rollback for model family '{model_family}'.")

        prev_id = active_dec.previous_promoted_version_id
        curr_id = active_dec.new_promoted_version_id

        # Fetch models
        stmt_curr = select(MLModelVersion).where(MLModelVersion.id == curr_id)
        curr_model = (await self.session.execute(stmt_curr)).scalar_one_or_none()

        stmt_prev = select(MLModelVersion).where(MLModelVersion.id == prev_id)
        prev_model = (await self.session.execute(stmt_prev)).scalar_one_or_none()

        if not prev_model:
            raise ValueError(f"Previous model version ID '{prev_id}' not found.")

        # Demote current and restore previous
        if curr_model:
            curr_model.lifecycle_status = "SUPERSEDED"
            await self.session.flush()
        prev_model.lifecycle_status = "PROMOTED"

        active_dec.is_active_authority = False

        rollback_dec = MLPromotionDecision(
            decision_id=f"ROLLBACK-{model_family[:6].upper()}-{uuid.uuid4().hex[:6]}",
            evaluation_id=active_dec.evaluation_id,
            model_family=model_family,
            previous_promoted_version_id=curr_id,
            previous_promoted_version=curr_model.model_version if curr_model else None,
            new_promoted_version_id=str(prev_model.id),
            new_promoted_version=prev_model.model_version,
            decision_type="ROLLED_BACK",
            authorized_by=authorized_by,
            authorization_reason=rollback_reason,
            is_active_authority=True,
            decision_timestamp=datetime.now(timezone.utc),
        )

        self.session.add(rollback_dec)
        await self.session.commit()
        logger.info(f"MODEL ROLLED BACK: {model_family} restored to {prev_model.model_version}")
        return rollback_dec
