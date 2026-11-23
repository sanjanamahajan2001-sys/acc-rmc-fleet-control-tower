"""
WS-10 Phase 5.8 Model Evaluation & Promotion API Router
Exposes endpoints for candidate model holdout evaluation, explicit promotion authorization, and model rollback.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.operational_intelligence.services.model_evaluation_service import ModelEvaluationService
from app.modules.operational_intelligence.services.model_promotion_service import ModelPromotionService

router = APIRouter(prefix="/operational-intelligence/evaluation", tags=["Operational Intelligence - Model Evaluation & Promotion"])


class EvaluateCandidateRequest(BaseModel):
    candidate_model_version_id: str
    evaluation_policy_version: Optional[str] = "WS58_PROMOTION_GATE_V1"
    custom_thresholds: Optional[Dict[str, Any]] = None


class PromoteCandidateRequest(BaseModel):
    candidate_model_version_id: str
    authorized_by: str = "AUTHORITATIVE_GOVERNANCE_ENGINE"
    authorization_reason: Optional[str] = "Passed WS5.8 holdout performance gates."


class RollbackModelRequest(BaseModel):
    model_family: str
    authorized_by: str = "AUTHORITATIVE_GOVERNANCE_ENGINE"
    rollback_reason: Optional[str] = "Manual rollback triggered due to performance anomaly."


@router.post("/evaluate")
async def evaluate_candidate_model(req: EvaluateCandidateRequest, db: AsyncSession = Depends(get_db_session)):
    """Evaluates candidate model version on reserved WS5.5 holdout dataset."""
    service = ModelEvaluationService(db)
    try:
        record = await service.evaluate_candidate_model(
            candidate_model_version_id=req.candidate_model_version_id,
            evaluation_policy_version=req.evaluation_policy_version or "WS58_PROMOTION_GATE_V1",
            custom_thresholds=req.custom_thresholds,
        )
        return {
            "evaluation_id": record.evaluation_id,
            "candidate_model_version_id": record.candidate_model_version_id,
            "candidate_version": record.candidate_version,
            "model_family": record.model_family,
            "dataset_id": record.dataset_id,
            "evaluation_status": record.evaluation_status,
            "promotion_recommendation": record.promotion_recommendation,
            "holdout_sample_count": record.holdout_sample_count,
            "metrics": record.metrics,
            "gate_results": record.gate_results,
            "rejection_reason": record.rejection_reason,
            "evaluated_at": record.evaluated_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/promote")
async def promote_candidate_model(req: PromoteCandidateRequest, db: AsyncSession = Depends(get_db_session)):
    """Atomically promotes a candidate model version to active PROMOTED inference authority."""
    service = ModelPromotionService(db)
    try:
        decision = await service.promote_candidate_model(
            candidate_model_version_id=req.candidate_model_version_id,
            authorized_by=req.authorized_by,
            authorization_reason=req.authorization_reason,
        )
        return {
            "decision_id": decision.decision_id,
            "model_family": decision.model_family,
            "previous_promoted_version": decision.previous_promoted_version,
            "new_promoted_version": decision.new_promoted_version,
            "decision_type": decision.decision_type,
            "authorized_by": decision.authorized_by,
            "is_active_authority": decision.is_active_authority,
            "decision_timestamp": decision.decision_timestamp.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rollback")
async def rollback_promoted_model(req: RollbackModelRequest, db: AsyncSession = Depends(get_db_session)):
    """Rolls back currently promoted model version to previous promoted version."""
    service = ModelPromotionService(db)
    try:
        decision = await service.rollback_promoted_model(
            model_family=req.model_family,
            authorized_by=req.authorized_by,
            rollback_reason=req.rollback_reason,
        )
        return {
            "decision_id": decision.decision_id,
            "model_family": decision.model_family,
            "previous_promoted_version": decision.previous_promoted_version,
            "new_promoted_version": decision.new_promoted_version,
            "decision_type": decision.decision_type,
            "authorized_by": decision.authorized_by,
            "is_active_authority": decision.is_active_authority,
            "decision_timestamp": decision.decision_timestamp.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
