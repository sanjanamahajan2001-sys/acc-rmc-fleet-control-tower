"""
WS-10 Phase 5.2: Outcome Matching Engine Service (`OutcomeMatchingService`).
Matches finalized authoritative ERP operational outcomes to active prediction snapshots using the authoritative prediction cutoff rule ($S_1 -> S_2 -> S_3$).
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome

logger = logging.getLogger(__name__)

SUPPORTED_MODEL_FAMILIES: List[str] = [
    "delay_regressor",
    "turnaround_regressor",
    "sla_breach_classifier",
    "plant_risk_classifier",
]


class OutcomeMatchingService:
    """
    WS5.2 Outcome Matching Engine.
    Matches finalized ERP dispatch outcomes to their authoritative MLPredictionSnapshot using prediction cutoff semantics ($S_1 -> S_2 -> S_3$).
    """

    @classmethod
    async def match_outcome_to_snapshot(
        cls,
        session: AsyncSession,
        dispatch_id: str,
        source_event_type: str = "ERP_DISPATCH_COMPLETED",
        force_recompute: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes the WS5.2 Outcome Matching algorithm for a finalized ERP dispatch.
        """
        start_time = datetime.now(timezone.utc)

        # 1. Query Dispatch and join plant, customer, vehicle context
        stmt = (
            select(Dispatch, Plant, Customer, Vehicle)
            .execution_options(populate_existing=True)
            .join(Plant, Dispatch.plant_id == Plant.id)
            .join(Customer, Dispatch.customer_id == Customer.id)
            .outerjoin(Vehicle, Dispatch.vehicle_id == Vehicle.id)
            .where(or_(Dispatch.id == dispatch_id, Dispatch.dispatch_number == dispatch_id))
        )
        res = await session.execute(stmt)
        row = res.one_or_none()

        if not row:
            logger.warning(f"[OUTCOME MATCHER] Dispatch '{dispatch_id}' not found.")
            return {
                "success": False,
                "reason": "DISPATCH_NOT_FOUND",
                "dispatch_id": dispatch_id,
                "matched_outcomes_count": 0,
            }

        disp, plant, cust, veh = row
        disp_raw_id = disp.id
        disp_uuid = str(disp.id)
        disp_code = disp.dispatch_number or f"DISP-{disp_uuid[:8].upper()}"

        # 2. Verify Dispatch Finality Contract (COMPLETED or CLOSED)
        if disp.status not in ("COMPLETED", "CLOSED"):
            logger.info(f"[OUTCOME MATCHER] Dispatch '{disp_code}' status '{disp.status}' is not finalized. Skipping matching.")
            return {
                "success": False,
                "reason": "DISPATCH_NOT_FINALIZED",
                "dispatch_id": disp_uuid,
                "dispatch_status": disp.status,
                "matched_outcomes_count": 0,
            }

        # 3. Extract Realized ERP Outcomes
        actual_transit = disp.t1_transit_mins
        actual_unloading = disp.t2b_unloading_mins or disp.unloading_duration_mins
        actual_holding = disp.t2a_holding_mins

        actual_sla_breach: Optional[bool] = None
        if actual_transit is not None and actual_unloading is not None:
            actual_sla_breach = (actual_transit + actual_unloading) > 120.0  # Contractual threshold

        actual_plant_risk: Optional[int] = None
        if actual_holding is not None:
            if actual_holding < 30.0:
                actual_plant_risk = 0  # NORMAL
            elif actual_holding < 60.0:
                actual_plant_risk = 1  # MODERATE
            else:
                actual_plant_risk = 2  # SEVERE

        outcome_timestamp = disp.date_in or disp.updated_at or datetime.now(timezone.utc)

        # 4. Idempotency Key & Existing Active Outcome Check
        base_ik = f"IK-OUT-{disp_code}-{source_event_type}-{outcome_timestamp.isoformat()}"

        stmt_existing = select(OperationalOutcome).where(
            OperationalOutcome.dispatch_id == disp_raw_id,
            OperationalOutcome.is_superseded == False,
        )
        existing_outcomes = list((await session.execute(stmt_existing)).scalars().all())

        if existing_outcomes and not force_recompute:
            # Check if existing outcome matches current ERP values
            active_out = existing_outcomes[0]
            if (
                active_out.actual_transit_mins == actual_transit
                and active_out.actual_unloading_mins == actual_unloading
            ):
                logger.info(f"[OUTCOME MATCHER] Outcome for dispatch '{disp_code}' already matched (ID: {active_out.outcome_id}).")
                return {
                    "success": True,
                    "reason": "OUTCOME_ALREADY_MATCHED",
                    "dispatch_id": disp_uuid,
                    "outcome_id": active_out.outcome_id,
                    "matched_outcomes_count": 1,
                }

        # 5. ERP Correction Handling (O1 -> O2 Lineage)
        superseded_outcome_id: Optional[str] = None
        rev_count = len(existing_outcomes)
        idempotency_key = base_ik if rev_count == 0 else f"{base_ik}-rev{rev_count+1}-{uuid.uuid4().hex[:4]}"

        if existing_outcomes:
            for old_out in existing_outcomes:
                new_superseded_id = f"OUT-{uuid.uuid4().hex[:8].upper()}"
                old_out.is_superseded = True
                old_out.superseded_by_outcome_id = new_superseded_id
                old_out.correction_reason = "ERP Outcome Value Correction"
                superseded_outcome_id = new_superseded_id
                logger.info(f"[OUTCOME MATCHER] Superseded prior outcome {old_out.outcome_id} -> {new_superseded_id}.")

        # 6. Authoritative Temporal Snapshot Selection Rule (S1 -> S2 -> S3 Cutoff Logic)
        new_outcome_id = superseded_outcome_id or f"OUT-{uuid.uuid4().hex[:8].upper()}"

        # Fetch all snapshots for dispatch ordered explicitly by prediction_timestamp ASC
        stmt_snaps = (
            select(MLPredictionSnapshot)
            .where(
                MLPredictionSnapshot.dispatch_id == disp_uuid,
                MLPredictionSnapshot.feature_set_version == "FeatureSetV1",
            )
            .order_by(MLPredictionSnapshot.prediction_timestamp.asc())
        )
        all_snapshots = list((await session.execute(stmt_snaps)).scalars().all())

        selected_snapshot: Optional[MLPredictionSnapshot] = None
        match_status_reason = "SUCCESS"

        if not all_snapshots:
            match_status_reason = "UNMATCHED_MISSING_SNAPSHOT"
            logger.warning(f"[OUTCOME MATCHER] No prediction snapshots found for dispatch '{disp_code}'.")
        else:
            # Build snapshot lookup dictionary for supersession timestamp resolution
            snap_by_id = {s.prediction_snapshot_id: s for s in all_snapshots}

            # Evaluate temporal authority interval for each snapshot: [T_start, T_end)
            authoritative_at_cutoff: List[MLPredictionSnapshot] = []

            for s in all_snapshots:
                t_start = s.prediction_timestamp

                # Determine authority interval upper bound T_end:
                # If superseded/stale: T_end is the exact invalidation timestamp (lineage_metadata.invalidated_at or updated_at),
                # or s_next.prediction_timestamp if next snapshot existed.
                if s.is_stale:
                    inv_ts = None
                    if s.lineage_metadata and isinstance(s.lineage_metadata, dict) and "invalidated_at" in s.lineage_metadata:
                        try:
                            inv_ts = datetime.fromisoformat(s.lineage_metadata["invalidated_at"])
                        except Exception:
                            inv_ts = s.updated_at
                    elif s.updated_at:
                        inv_ts = s.updated_at

                    if s.superseded_by_snapshot_id and s.superseded_by_snapshot_id in snap_by_id:
                        s_next = snap_by_id[s.superseded_by_snapshot_id]
                        t_end = min(inv_ts, s_next.prediction_timestamp) if inv_ts else s_next.prediction_timestamp
                    elif inv_ts:
                        t_end = inv_ts
                    else:
                        t_end = t_start
                else:
                    t_end = datetime.max.replace(tzinfo=timezone.utc)

                # Strict Authority Interval Check: T_start <= outcome_timestamp < T_end
                if t_start <= outcome_timestamp < t_end:
                    authoritative_at_cutoff.append(s)

            if authoritative_at_cutoff:
                # Select latest prediction snapshot whose authority interval contained the outcome cutoff
                # Explicit ORDER BY prediction_timestamp DESC, prediction_snapshot_id DESC
                authoritative_at_cutoff.sort(key=lambda s: (s.prediction_timestamp, s.prediction_snapshot_id), reverse=True)
                selected_snapshot = authoritative_at_cutoff[0]
            else:
                # NO STALE FALLBACK: If no snapshot was authoritative at cutoff, return UNMATCHED_MISSING_SNAPSHOT
                match_status_reason = "UNMATCHED_MISSING_SNAPSHOT"
                logger.warning(
                    f"[OUTCOME MATCHER] No prediction snapshot was authoritative for dispatch '{disp_code}' "
                    f"at cutoff timestamp {outcome_timestamp.isoformat()}. Stale fallback PROHIBITED."
                )

        # 7. Verification Barrier & Late Outcome Marking
        is_late_arrival = False
        if selected_snapshot:
            time_delta = outcome_timestamp - selected_snapshot.prediction_timestamp
            if time_delta > timedelta(minutes=15):
                is_late_arrival = True

        # Validation Rule Check: physical bound sanity
        is_validated = True
        if actual_transit is not None and (actual_transit < 0.0 or actual_transit > 1440.0):
            is_validated = False
        if actual_unloading is not None and (actual_unloading < 0.0 or actual_unloading > 1440.0):
            is_validated = False

        verification_status = "RECEIVED"
        is_verified = False

        if is_validated and match_status_reason == "SUCCESS":
            verification_status = "VERIFIED"
            is_verified = True
        elif not is_validated:
            verification_status = "VALIDATION_FAILED"

        audit_meta = {
            "source_event_type": source_event_type,
            "match_status": match_status_reason,
            "is_late_arrival": is_late_arrival,
            "matched_snapshot_id": selected_snapshot.prediction_snapshot_id if selected_snapshot else None,
            "matched_at": datetime.now(timezone.utc).isoformat(),
        }

        # 8. Create and Persist OperationalOutcome
        outcome = OperationalOutcome(
            outcome_id=new_outcome_id,
            dispatch_id=disp_raw_id,
            dispatch_code=disp_code,
            prediction_snapshot_id=selected_snapshot.prediction_snapshot_id if selected_snapshot else None,
            idempotency_key=idempotency_key,
            actual_transit_mins=actual_transit,
            actual_unloading_mins=actual_unloading,
            actual_sla_breach_flag=actual_sla_breach,
            actual_plant_risk_class=actual_plant_risk,
            actual_financial_impact_inr=None,
            verification_status=verification_status,
            is_verified=is_verified,
            is_superseded=False,
            outcome_timestamp=outcome_timestamp,
            source_event_type=source_event_type,
            audit_metadata=audit_meta,
        )
        session.add(outcome)
        await session.commit()

        logger.info(
            f"[OUTCOME MATCHER] Matched dispatch '{disp_code}' outcome '{new_outcome_id}' to snapshot "
            f"'{selected_snapshot.prediction_snapshot_id if selected_snapshot else 'NONE'}' (verified={is_verified})."
        )

        return {
            "success": True,
            "reason": match_status_reason,
            "dispatch_id": disp_uuid,
            "dispatch_code": disp_code,
            "outcome_id": new_outcome_id,
            "matched_snapshot_id": selected_snapshot.prediction_snapshot_id if selected_snapshot else None,
            "verification_status": verification_status,
            "is_verified": is_verified,
            "is_late_arrival": is_late_arrival,
            "matched_outcomes_count": 1,
            "execution_duration_sec": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }
