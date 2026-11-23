import asyncio
import json
from sqlalchemy import select, text
from app.core.database import AsyncSessionFactory
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import PredictionRequestDTO
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService

async def main():
    async with AsyncSessionFactory() as session:
        # Check active promoted models
        res_prom = await session.execute(select(MLModelVersion).where(MLModelVersion.lifecycle_status == "PROMOTED"))
        promoted = list(res_prom.scalars().all())
        print(f"Active Promoted Models: {len(promoted)}")

        # Query real dispatches with plant and customer JOINs
        sql = text("""
            SELECT 
                d.id AS dispatch_id,
                p.code AS plant_code,
                c.code AS customer_code,
                v.code AS vehicle_code,
                d.ticket_volume_m3,
                d.t2a_holding_mins,
                d.t2c_retention_mins,
                d.date_in
            FROM dispatches d
            LEFT JOIN plants p ON d.plant_id = p.id
            LEFT JOIN customers c ON d.customer_id = c.id
            LEFT JOIN vehicles v ON d.vehicle_id = v.id
            WHERE p.code IS NOT NULL AND c.code IS NOT NULL
            ORDER BY d.created_at DESC
            LIMIT 50
        """)
        res = await session.execute(sql)
        rows = res.fetchall()
        print(f"Found {len(rows)} real dispatches with resolved plant and customer codes.")

        created_count = 0
        for r in rows:
            disp_code = f"DISP-{str(r.dispatch_id)[:8].upper()}"
            plant_code = r.plant_code
            customer_code = r.customer_code
            vehicle_code = r.vehicle_code or "V-REAL"
            ticket_vol = float(r.ticket_volume_m3 or 10.0)
            date_str = str(r.date_in)[:10] if r.date_in else "2026-08-05"

            req = PredictionRequestDTO(
                dispatch_id=str(r.dispatch_id),
                dispatch_code=disp_code,
                plant_code=plant_code,
                customer_code=customer_code,
                vehicle_code=vehicle_code,
                ticket_volume_m3=ticket_vol,
                plant_queue_avg_30d=float(r.t2a_holding_mins or 12.0),
                customer_retention_avg_30d=float(r.t2c_retention_mins or 5.0),
                dispatch_hour=10,
                dispatch_day_of_week=2,
                input_features={
                    "operation_date": date_str,
                    "plant_code": plant_code,
                    "customer_code": customer_code,
                    "vehicle_code": vehicle_code,
                    "ticket_volume_m3": ticket_vol,
                }
            )

            # Generate snapshots for all promoted models
            for p in promoted:
                try:
                    await WS10InferenceService.execute_inference_and_persist_snapshot(
                        session=session,
                        model_name=p.model_name,
                        request=req
                    )
                    created_count += 1
                except Exception as e:
                    print(f"Error creating snapshot for {p.model_name}: {e}")

        await session.commit()
        print(f"Successfully generated {created_count} real prediction snapshots for real ERP dispatches!")

if __name__ == "__main__":
    asyncio.run(main())
