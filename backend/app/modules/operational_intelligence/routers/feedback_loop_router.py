from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.operational_intelligence.services.feedback_loop_service import FeedbackLoopService

router = APIRouter(prefix="/operational-intelligence/feedback", tags=["Operational Intelligence - Feedback Loop"])

class FeedbackIngestRequest(BaseModel):
    outcome_id: str
    planner_action: Optional[str] = None

class TriggerEvaluateRequest(BaseModel):
    model_family: str
    threshold_mae: Optional[float] = 15.0
    threshold_acc: Optional[float] = 0.80

@router.post("/ingest")
async def ingest_feedback(req: FeedbackIngestRequest, db: AsyncSession = Depends(get_db_session)):
    """Ingests verified operational outcome and matches it against prediction snapshots."""
    service = FeedbackLoopService(db)
    try:
        res = await service.ingest_feedback_for_outcome(req.outcome_id, req.planner_action)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/triggers/evaluate")
async def evaluate_triggers(req: TriggerEvaluateRequest, db: AsyncSession = Depends(get_db_session)):
    """Evaluates continuous learning triggers and retrain recommendations for a model family."""
    service = FeedbackLoopService(db)
    res = await service.evaluate_continuous_learning_triggers(
        model_family=req.model_family,
        threshold_mae=req.threshold_mae or 15.0,
        threshold_acc=req.threshold_acc or 0.80,
    )
    return res
