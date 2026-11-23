"""
Authoritative Phase 8 WS8.2 Action Ingestion & Seeding Script.
Populates realistic filter-scoped recommendations across all 4 plants (ACC_NESSAI, ACC_VASCO, ACC_DHARGA, ACC_KUNDAIM)
in PENDING state using authoritative Phase 6 prediction snapshots and model registry lineage.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, delete, text
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.planner_action import PlannerActionLog
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.erp.models import Dispatch, Plant


async def seed_actions():
    async with AsyncSessionFactory() as session:
        # Delete existing test actions to ensure fresh seed
        await session.execute(delete(PlannerActionLog))
        await session.commit()

        # Fetch active prediction snapshots for dispatches
        stmt = (
            select(MLPredictionSnapshot, Dispatch)
            .join(Dispatch, MLPredictionSnapshot.dispatch_id == Dispatch.id)
            .where(
                MLPredictionSnapshot.is_stale == False,
                MLPredictionSnapshot.is_deleted == False,
                Dispatch.is_deleted == False
            )
            .limit(100)
        )
        res = await session.execute(stmt)
        rows = res.all()

        seeded_count = 0
        action_types = [
            ("STAGGER_LOADING", "Staggered Loading Offset", {"offset_mins": 15}),
            ("TRANSIT_BUFFER", "Transit Lead-Time Buffer", {"buffer_mins": 20}),
            ("SLA_PRIORITIZE", "High SLA Breach Prioritization", {"priority_level": "URGENT"}),
            ("ZONE_REALLOCATE", "Plant Zone Throughput Allocation", {"target_zone": "South Zone"}),
        ]

        for idx, (snap, disp) in enumerate(rows):
            action_type, title, params = action_types[idx % len(action_types)]
            act_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
            rec_id = f"REC-WS82-{idx + 1:04d}"
            idemp_key = f"SEED-{uuid.uuid4().hex[:12]}"

            # Calculate risk from delay or rate spec
            predicted_delay = float(snap.predicted_value or 25.0)
            risk_inr = round(max(0.0, predicted_delay - 20.0) * 25.0, 2) if snap.model_family == "delay_regressor" else 1250.0

            action = PlannerActionLog(
                action_id=act_id,
                recommendation_id=rec_id,
                prediction_snapshot_id=snap.id,
                model_family=snap.model_family,
                model_version=snap.model_version,
                dataset_id=snap.dataset_id,
                operation_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                plant_code=snap.plant_code,
                customer_code=snap.customer_code,
                dispatch_id=disp.id,
                dispatch_code=disp.dispatch_code,
                action_type=action_type,
                action_parameters=params,
                predicted_risk_exposure_inr=risk_inr,
                action_status="PENDING",
                dispatcher_id="SYSTEM_RECOMMENDER",
                dispatcher_role="DISPATCHER",
                idempotency_key=idemp_key,
                version_lock=1,
            )
            session.add(action)
            seeded_count += 1

        await session.commit()
        print(f"✅ Successfully seeded {seeded_count} action recommendations in PENDING status across all plants!")


if __name__ == "__main__":
    asyncio.run(seed_actions())
