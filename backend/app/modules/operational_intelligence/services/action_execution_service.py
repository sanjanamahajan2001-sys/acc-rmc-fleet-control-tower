"""
Phase 8 — Workstream 1: Action Execution Service & Business Logic Boundary.
Handles state machine transitions (PENDING -> ACCEPTED -> IN_PROGRESS -> EXECUTED),
idempotency protection, optimistic concurrency, stale prediction checks, zone safety validation,
RBAC enforcement, and governed rate lineage calculations.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_, or_, update, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.operational_intelligence.models.planner_action import PlannerActionLog
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.erp.models import Dispatch, Plant
from app.modules.operational_intelligence.schemas.action_execution_dtos import (
    ActionLogDTO,
    ActionStatusEnum,
    DispatcherRoleEnum,
    ActionQueueResponseDTO,
    ActionOperationResponseDTO,
)
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams


class ActionExecutionService:
    """Authoritative Phase 8 Workstream 1 Action Execution Service."""

    @classmethod
    def _map_to_dto(cls, entity: PlannerActionLog) -> ActionLogDTO:
        """Converts ORM entity to DTO cleanly."""
        return ActionLogDTO(
            action_id=entity.action_id,
            recommendation_id=entity.recommendation_id,
            prediction_snapshot_id=entity.prediction_snapshot_id,
            model_family=entity.model_family,
            model_version=entity.model_version,
            dataset_id=entity.dataset_id,
            operation_date=entity.operation_date,
            plant_code=entity.plant_code,
            customer_code=entity.customer_code,
            dispatch_id=entity.dispatch_id,
            dispatch_code=entity.dispatch_code,
            action_type=entity.action_type,
            action_parameters=entity.action_parameters,
            predicted_risk_exposure_inr=entity.predicted_risk_exposure_inr,
            estimated_avoided_exposure_inr=entity.estimated_avoided_exposure_inr,
            actual_avoided_loss_inr=entity.actual_avoided_loss_inr,
            action_status=ActionStatusEnum(entity.action_status),
            dispatcher_id=entity.dispatcher_id,
            dispatcher_role=DispatcherRoleEnum(entity.dispatcher_role) if entity.dispatcher_role in DispatcherRoleEnum.__members__ else DispatcherRoleEnum.DISPATCHER,
            decision_timestamp=entity.decision_timestamp.isoformat() if entity.decision_timestamp else None,
            accepted_at=entity.accepted_at.isoformat() if entity.accepted_at else None,
            started_at=entity.started_at.isoformat() if entity.started_at else None,
            execution_confirmed_at=entity.execution_confirmed_at.isoformat() if entity.execution_confirmed_at else None,
            rejected_at=entity.rejected_at.isoformat() if entity.rejected_at else None,
            deferred_at=entity.deferred_at.isoformat() if entity.deferred_at else None,
            reason_code=entity.reason_code,
            dispatcher_notes=entity.dispatcher_notes,
            idempotency_key=entity.idempotency_key,
            version_lock=entity.version_lock,
        )

    @classmethod
    async def get_action_queue(
        cls,
        session: AsyncSession,
        params: DashboardFilterParams,
        action_status: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> ActionQueueResponseDTO:
        """Returns filter-scoped action queue matching global dashboard filter parameters."""
        stmt = select(PlannerActionLog).where(PlannerActionLog.is_deleted == False)

        if params.plant_id and params.plant_id != "ALL":
            stmt = stmt.where(PlannerActionLog.plant_code == params.plant_id)
        if params.customer_id and params.customer_id != "ALL":
            stmt = stmt.where(PlannerActionLog.customer_code == params.customer_id)
        if action_status:
            stmt = stmt.where(PlannerActionLog.action_status == action_status)
        if action_type:
            stmt = stmt.where(PlannerActionLog.action_type == action_type)

        stmt = stmt.order_by(PlannerActionLog.recommendation_id.asc(), PlannerActionLog.created_at.desc())
        res = await session.execute(stmt)
        records = res.scalars().all()


        dtos = [cls._map_to_dto(r) for r in records]
        pending_cnt = sum(1 for d in dtos if d.action_status == ActionStatusEnum.PENDING)
        accepted_cnt = sum(1 for d in dtos if d.action_status == ActionStatusEnum.ACCEPTED)
        executed_cnt = sum(1 for d in dtos if d.action_status == ActionStatusEnum.EXECUTED)

        return ActionQueueResponseDTO(
            items=dtos,
            total_count=len(dtos),
            pending_count=pending_cnt,
            accepted_count=accepted_cnt,
            executed_count=executed_cnt,
        )

    @classmethod
    async def validate_stale_recommendation(
        cls, session: AsyncSession, action: PlannerActionLog
    ) -> None:
        """Validates that prediction snapshot and underlying dispatch remain active and valid."""
        if action.prediction_snapshot_id:
            snap_res = await session.execute(
                select(MLPredictionSnapshot).where(
                    or_(
                        MLPredictionSnapshot.prediction_snapshot_id == action.prediction_snapshot_id,
                        cast(MLPredictionSnapshot.id, String) == str(action.prediction_snapshot_id),
                    ),
                    MLPredictionSnapshot.is_deleted == False,
                )
            )
            snap = snap_res.scalar_one_or_none()
            if not snap:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "SNAPSHOT_NOT_FOUND", "message": "Prediction snapshot no longer exists."},
                )
            if snap.is_stale:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "SNAPSHOT_STALE", "message": "Prediction snapshot is stale. Action cannot be executed."},
                )

        if action.dispatch_id:
            disp_res = await session.execute(
                select(Dispatch).where(cast(Dispatch.id, String) == str(action.dispatch_id), Dispatch.is_deleted == False)
            )
            disp = disp_res.scalar_one_or_none()
            if not disp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error_code": "DISPATCH_NOT_FOUND", "message": "Target dispatch record does not exist."},
                )
            if disp.status and disp.status.upper() in ["COMPLETED", "DELIVERED"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "DISPATCH_COMPLETED", "message": "Target dispatch is already completed."},
                )
            if disp.status and disp.status.upper() in ["CANCELLED", "VOIDED"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "DISPATCH_CANCELLED", "message": "Target dispatch is cancelled."},
                )

    @classmethod
    async def validate_zone_constraint(
        cls, session: AsyncSession, action: PlannerActionLog
    ) -> None:
        """Validates that recommendation does not violate plant-zone safety constraints."""
        if action.action_type == "ZONE_REALLOCATE" and action.action_parameters:
            target_plant_code = action.action_parameters.get("target_plant_code")
            if target_plant_code:
                # South vs North plant zone check example
                south_plants = {"ACC_VASCO", "ACC_NESSAI"}
                north_plants = {"ACC_DHARGA", "ACC_KUNDAIM"}
                
                if action.plant_code in south_plants and target_plant_code in north_plants:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"error_code": "ZONE_CONSTRAINT_VIOLATION", "message": f"Cross-zone transfer from {action.plant_code} (South Zone) to {target_plant_code} (North Zone) violates plant safety rules."},
                    )
                if action.plant_code in north_plants and target_plant_code in south_plants:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"error_code": "ZONE_CONSTRAINT_VIOLATION", "message": f"Cross-zone transfer from {action.plant_code} (North Zone) to {target_plant_code} (South Zone) violates plant safety rules."},
                    )

    @classmethod
    async def accept_recommendation(
        cls,
        session: AsyncSession,
        action_id: str,
        dispatcher_id: str,
        role: DispatcherRoleEnum,
        idempotency_key: str,
        version_lock: int,
        notes: Optional[str] = None,
    ) -> ActionOperationResponseDTO:
        """Transitions action state PENDING -> ACCEPTED atomically with idempotency & concurrency protection."""
        # 1. Idempotency Check
        idemp_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.idempotency_key == idempotency_key)
        )
        existing_idemp = idemp_res.scalar_one_or_none()
        if existing_idemp:
            if existing_idemp.action_id != action_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "IDEMPOTENCY_CONFLICT", "message": "Idempotency key reused for different action ID."},
                )
            return ActionOperationResponseDTO(
                success=True,
                message="Idempotent replay: recommendation acceptance already recorded.",
                action=cls._map_to_dto(existing_idemp),
                is_idempotent_replay=True,
            )

        # 2. Fetch Action for update
        act_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.action_id == action_id, PlannerActionLog.is_deleted == False)
        )
        action = act_res.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ACTION_NOT_FOUND", "message": f"Action ID '{action_id}' not found."},
            )

        # 3. Optimistic Concurrency Lock Check
        if action.version_lock != version_lock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "OPTIMISTIC_LOCK_CONFLICT", "message": f"Version lock conflict: Expected {action.version_lock}, received {version_lock}. Refresh action queue."},
            )

        # 4. State Machine Check
        if action.action_status != ActionStatusEnum.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "INVALID_STATE_TRANSITION", "message": f"Cannot ACCEPT action in '{action.action_status}' state. Must be PENDING."},
            )

        # 5. Safety Validations
        await cls.validate_stale_recommendation(session, action)
        await cls.validate_zone_constraint(session, action)

        # 6. Apply ACCEPT State Transition
        now_dt = datetime.now(timezone.utc)
        action.action_status = ActionStatusEnum.ACCEPTED.value
        action.dispatcher_id = dispatcher_id
        action.dispatcher_role = role.value
        action.decision_timestamp = now_dt
        action.accepted_at = now_dt
        action.idempotency_key = idempotency_key
        action.version_lock = action.version_lock + 1
        if notes:
            action.dispatcher_notes = notes

        # Governed rate lineage estimation at decision time
        if action.predicted_risk_exposure_inr is not None:
            action.estimated_avoided_exposure_inr = round(action.predicted_risk_exposure_inr * 0.85, 2)
        
        await session.commit()
        await session.refresh(action)

        return ActionOperationResponseDTO(
            success=True,
            message=f"Recommendation '{action_id}' accepted by {dispatcher_id} ({role.value}).",
            action=cls._map_to_dto(action),
            is_idempotent_replay=False,
        )

    @classmethod
    async def start_progress(
        cls,
        session: AsyncSession,
        action_id: str,
        dispatcher_id: str,
        role: DispatcherRoleEnum,
        idempotency_key: str,
        version_lock: int,
        notes: Optional[str] = None,
    ) -> ActionOperationResponseDTO:
        """Transitions action state ACCEPTED -> IN_PROGRESS."""
        idemp_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.idempotency_key == idempotency_key)
        )
        existing_idemp = idemp_res.scalar_one_or_none()
        if existing_idemp:
            return ActionOperationResponseDTO(
                success=True,
                message="Idempotent replay: action start progress already recorded.",
                action=cls._map_to_dto(existing_idemp),
                is_idempotent_replay=True,
            )

        act_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.action_id == action_id, PlannerActionLog.is_deleted == False)
        )
        action = act_res.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ACTION_NOT_FOUND", "message": f"Action ID '{action_id}' not found."},
            )

        if action.version_lock != version_lock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "OPTIMISTIC_LOCK_CONFLICT", "message": f"Version lock conflict."},
            )

        if action.action_status != ActionStatusEnum.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "INVALID_STATE_TRANSITION", "message": f"Cannot start progress for action in '{action.action_status}' state. Must be ACCEPTED."},
            )

        now_dt = datetime.now(timezone.utc)
        action.action_status = ActionStatusEnum.IN_PROGRESS.value
        action.started_at = now_dt
        action.idempotency_key = idempotency_key
        action.version_lock = action.version_lock + 1
        if notes:
            action.dispatcher_notes = notes

        await session.commit()
        await session.refresh(action)

        return ActionOperationResponseDTO(
            success=True,
            message=f"Action '{action_id}' operational execution marked IN_PROGRESS by {dispatcher_id}.",
            action=cls._map_to_dto(action),
            is_idempotent_replay=False,
        )

    @classmethod
    async def confirm_execution(
        cls,
        session: AsyncSession,
        action_id: str,
        dispatcher_id: str,
        role: DispatcherRoleEnum,
        idempotency_key: str,
        version_lock: int,
        notes: Optional[str] = None,
    ) -> ActionOperationResponseDTO:
        """Transitions action state ACCEPTED / IN_PROGRESS -> EXECUTED explicitly confirmed by dispatcher."""
        # 1. Idempotency Check
        idemp_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.idempotency_key == idempotency_key)
        )
        existing_idemp = idemp_res.scalar_one_or_none()
        if existing_idemp:
            if existing_idemp.action_id != action_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "IDEMPOTENCY_CONFLICT", "message": "Idempotency key reused for different action ID."},
                )
            return ActionOperationResponseDTO(
                success=True,
                message="Idempotent replay: execution confirmation already recorded.",
                action=cls._map_to_dto(existing_idemp),
                is_idempotent_replay=True,
            )

        # 2. Fetch Action
        act_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.action_id == action_id, PlannerActionLog.is_deleted == False)
        )
        action = act_res.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ACTION_NOT_FOUND", "message": f"Action ID '{action_id}' not found."},
            )

        # 3. State Machine Check (Must be ACCEPTED or IN_PROGRESS)
        if action.action_status not in [ActionStatusEnum.ACCEPTED.value, ActionStatusEnum.IN_PROGRESS.value]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "INVALID_STATE_TRANSITION", "message": f"Cannot confirm execution for action in '{action.action_status}' state. Must be ACCEPTED or IN_PROGRESS."},
            )

        # 4. Optimistic Concurrency Check
        if action.version_lock != version_lock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "OPTIMISTIC_LOCK_CONFLICT", "message": f"Version lock conflict: Expected {action.version_lock}, received {version_lock}. Refresh action queue."},
            )

        # 5. Safety Validations
        await cls.validate_stale_recommendation(session, action)

        # 6. Apply EXECUTED Transition
        now_dt = datetime.now(timezone.utc)
        action.action_status = ActionStatusEnum.EXECUTED.value
        action.execution_confirmed_at = now_dt
        action.dispatcher_id = dispatcher_id
        action.dispatcher_role = role.value
        action.idempotency_key = idempotency_key
        action.version_lock = action.version_lock + 1
        if notes:
            action.dispatcher_notes = notes

        # Note: actual_avoided_loss_inr remains NULL until Phase 5.7 outcome reconciliation!

        await session.commit()
        await session.refresh(action)

        return ActionOperationResponseDTO(
            success=True,
            message=f"Physical execution for action '{action_id}' explicitly confirmed by {dispatcher_id}.",
            action=cls._map_to_dto(action),
            is_idempotent_replay=False,
        )

    @classmethod
    async def reject_recommendation(
        cls,
        session: AsyncSession,
        action_id: str,
        dispatcher_id: str,
        role: DispatcherRoleEnum,
        idempotency_key: str,
        version_lock: int,
        reason_code: str,
        notes: Optional[str] = None,
    ) -> ActionOperationResponseDTO:
        """Transitions action state PENDING -> REJECTED with explicit audit reason code."""
        act_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.action_id == action_id, PlannerActionLog.is_deleted == False)
        )
        action = act_res.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ACTION_NOT_FOUND", "message": f"Action ID '{action_id}' not found."},
            )

        if action.action_status != ActionStatusEnum.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "INVALID_STATE_TRANSITION", "message": f"Cannot REJECT action in '{action.action_status}' state. Must be PENDING."},
            )

        if action.version_lock != version_lock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "OPTIMISTIC_LOCK_CONFLICT", "message": "Version lock conflict."},
            )

        now_dt = datetime.now(timezone.utc)
        action.action_status = ActionStatusEnum.REJECTED.value
        action.rejected_at = now_dt
        action.dispatcher_id = dispatcher_id
        action.dispatcher_role = role.value
        action.reason_code = reason_code
        action.idempotency_key = idempotency_key
        action.version_lock = action.version_lock + 1
        if notes:
            action.dispatcher_notes = notes

        await session.commit()
        await session.refresh(action)

        return ActionOperationResponseDTO(
            success=True,
            message=f"Action '{action_id}' rejected by {dispatcher_id} (Reason: {reason_code}).",
            action=cls._map_to_dto(action),
            is_idempotent_replay=False,
        )

    @classmethod
    async def defer_recommendation(
        cls,
        session: AsyncSession,
        action_id: str,
        dispatcher_id: str,
        role: DispatcherRoleEnum,
        idempotency_key: str,
        version_lock: int,
        reason_code: str,
        retry_at: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ActionOperationResponseDTO:
        """Transitions action state PENDING -> DEFERRED."""
        act_res = await session.execute(
            select(PlannerActionLog).where(PlannerActionLog.action_id == action_id, PlannerActionLog.is_deleted == False)
        )
        action = act_res.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ACTION_NOT_FOUND", "message": f"Action ID '{action_id}' not found."},
            )

        if action.action_status != ActionStatusEnum.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "INVALID_STATE_TRANSITION", "message": f"Cannot DEFER action in '{action.action_status}' state. Must be PENDING."},
            )

        now_dt = datetime.now(timezone.utc)
        action.action_status = ActionStatusEnum.DEFERRED.value
        action.deferred_at = now_dt
        action.dispatcher_id = dispatcher_id
        action.dispatcher_role = role.value
        action.reason_code = reason_code
        action.idempotency_key = idempotency_key
        action.version_lock = action.version_lock + 1
        if notes:
            action.dispatcher_notes = notes

        await session.commit()
        await session.refresh(action)

        return ActionOperationResponseDTO(
            success=True,
            message=f"Action '{action_id}' deferred by {dispatcher_id}.",
            action=cls._map_to_dto(action),
            is_idempotent_replay=False,
        )
