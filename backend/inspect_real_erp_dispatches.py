import asyncio
import json
from sqlalchemy import select, func
from app.core.database import AsyncSessionFactory
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle

async def main():
    async with AsyncSessionFactory() as session:
        # Sample 10 real dispatches from dispatches table
        res_disp = await session.execute(
            select(Dispatch).order_by(Dispatch.created_at.desc()).limit(10)
        )
        dispatches = list(res_disp.scalars().all())

        # Sample real plants
        res_plant = await session.execute(select(Plant).limit(5))
        plants = [p.plant_code for p in res_plant.scalars().all()]

        # Sample real customers
        res_cust = await session.execute(select(Customer).limit(5))
        customers = [c.customer_code for c in res_cust.scalars().all()]

        # Sample real vehicles
        res_veh = await session.execute(select(Vehicle).limit(5))
        vehicles = [v.vehicle_code for v in res_veh.scalars().all()]

        disp_data = [
            {
                "id": str(d.id),
                "dispatch_code": d.dispatch_code,
                "plant_id": str(d.plant_id),
                "customer_id": str(d.customer_id),
                "vehicle_id": str(d.vehicle_id),
                "ticket_volume_m3": d.ticket_volume_m3,
                "t1_transit_mins": d.t1_transit_mins,
                "date_in": str(d.date_in) if d.date_in else None,
            }
            for d in dispatches
        ]

        report = {
            "sample_real_plants": plants,
            "sample_real_customers": customers,
            "sample_real_vehicles": vehicles,
            "sample_real_dispatches": disp_data,
        }

        print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
