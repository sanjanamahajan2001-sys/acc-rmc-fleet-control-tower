"""
Production Predictive Data Generation Script
Generates prediction snapshots across ALL plants (ACC_VASCO, ACC_NESSAI, ACC_DHARGA, ACC_KUNDAIM), customers, and dispatches.
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.core.database import AsyncSessionFactory
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_predictive_data")

async def main():
    # 0. Ensure tables exist & clean stale snapshots
    async with AsyncSessionFactory() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS ml_batch_processing_cursors (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                batch_job_name VARCHAR(100) NOT NULL UNIQUE,
                last_processed_timestamp TIMESTAMP WITH TIME ZONE,
                last_processed_dispatch_id VARCHAR(100),
                total_dispatches_processed BIGINT NOT NULL DEFAULT 0,
                total_snapshots_generated BIGINT NOT NULL DEFAULT 0,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                created_by UUID,
                updated_by UUID
            );
        """))
        await session.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_batch_processing_cursors_batch_job_name ON ml_batch_processing_cursors (batch_job_name);"))
        await session.execute(text("TRUNCATE TABLE ml_prediction_snapshots CASCADE;"))
        await session.commit()
        logger.info("Ensured ml_batch_processing_cursors table and truncated ml_prediction_snapshots.")

    # 1. Query dispatches across ALL plants, customers, and vehicles in the database
    async with AsyncSessionFactory() as session:
        stmt = (
            select(Dispatch, Plant, Customer, Vehicle)
            .outerjoin(Plant, Dispatch.plant_id == Plant.id)
            .outerjoin(Customer, Dispatch.customer_id == Customer.id)
            .outerjoin(Vehicle, Dispatch.vehicle_id == Vehicle.id)
            .order_by(Dispatch.created_at.desc())
        )
        res = await session.execute(stmt)
        rows = res.all()
        logger.info(f"Fetched {len(rows)} real dispatches across ALL plants and customers from database.")

    if not rows:
        logger.warning("No dispatches found in database!")
        return

    created_count = 0
    model_families = [
        "delay_regressor",
        "turnaround_regressor",
        "sla_breach_classifier",
        "plant_risk_classifier",
    ]

    base_date = datetime(2026, 8, 5, 10, 0, 0, tzinfo=timezone.utc)

    for idx, (disp, plant, cust, veh) in enumerate(rows):
        disp_code = disp.dispatch_number or f"DISP-{str(disp.id)[:8].upper()}"
        plant_code = (plant.code if plant and plant.code else (plant.name if plant and plant.name else "ACC_VASCO"))
        customer_code = (cust.code if cust and cust.code else (cust.name if cust and cust.name else "CUST_GENERAL"))
        vehicle_code = (veh.code if veh and veh.code else "V-101")

        # Guarantee operation date matches 2026-08-05 for UI selection
        dt = disp.date_in or base_date
        date_str = "2026-08-05"
        hour = (idx % 12) + 7
        day_of_week = 2

        raw_holding = float(disp.t2a_holding_mins if disp.t2a_holding_mins is not None else 15.0)
        holding_mins = min(raw_holding, 35.0)
        retention_mins = float(disp.t2c_retention_mins if disp.t2c_retention_mins is not None else 8.0)
        ticket_vol = float(getattr(disp, "qty_m3", 6.0) or 6.0)

        req = PredictionRequestDTO(
            dispatch_id=str(disp.id),
            dispatch_code=disp_code,
            plant_code=plant_code,
            customer_code=customer_code,
            vehicle_code=vehicle_code,
            ticket_volume_m3=ticket_vol,
            plant_queue_avg_30d=holding_mins,
            customer_retention_avg_30d=retention_mins,
            dispatch_hour=hour,
            dispatch_day_of_week=day_of_week,
            prediction_timestamp=base_date,
            input_features={
                "operation_date": date_str,
                "plant_code": plant_code,
                "customer_code": customer_code,
                "vehicle_code": vehicle_code,
                "ticket_volume_m3": ticket_vol,
                "plant_queue_avg_30d": holding_mins,
                "customer_retention_avg_30d": retention_mins,
                "dispatch_hour": hour,
                "dispatch_day_of_week": day_of_week,
            },
        )

        for m_name in model_families:
            try:
                async with AsyncSessionFactory() as session:
                    snap_repo = MLPredictionSnapshotRepository(session)
                    await snap_repo.generate_and_persist_prediction_snapshot(m_name, req)
                    await session.commit()
                    created_count += 1
            except Exception as e:
                logger.error(f"Snapshot failed for {m_name} on {disp_code}: {e}")

    logger.info(f"Generated {created_count} prediction snapshots across ALL plants and customers.")
    logger.info("=== PREDICTIVE DATA GENERATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
