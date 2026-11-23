import asyncio
from app.core.database import AsyncSessionFactory
from sqlalchemy import select, func
from app.modules.operational_intelligence.models.planner_action import PlannerActionLog
from app.modules.erp.models import Dispatch

async def main():
    async with AsyncSessionFactory() as session:
        res1 = await session.execute(select(PlannerActionLog.action_type, func.count(PlannerActionLog.action_id)).group_by(PlannerActionLog.action_type))
        breakdown = dict(res1.fetchall())
        
        disp_res = await session.execute(select(func.count(Dispatch.id)).where(Dispatch.is_deleted == False))
        total_disp = disp_res.scalar_one()

        rec_disp_res = await session.execute(select(func.count(func.distinct(PlannerActionLog.dispatch_id))))
        rec_disp = rec_disp_res.scalar_one()

        print("=== WS8.3 POPULATION BREAKDOWN RECONCILIATION ===")
        print(f"Total Dispatches: {total_disp}")
        print(f"Total Dispatches with Actions: {rec_disp}")
        print(f"No Action Dispatches (Below Thresholds): {total_disp - rec_disp}")
        print("Action Type Breakdown:")
        for k, v in breakdown.items():
            print(f"  • {k}: {v}")

        # Fetch 3 samples of INTRA_ZONE_REALLOCATE to inspect counterfactual evidence
        realloc_res = await session.execute(select(PlannerActionLog).where(PlannerActionLog.action_type == 'INTRA_ZONE_REALLOCATE').limit(3))
        samples = realloc_res.scalars().all()
        print("\n=== INTRA_ZONE_REALLOCATE COUNTERFACTUAL SAMPLE PROOF ===")
        for s in samples:
            print(f"Dispatch {s.dispatch_code} | Plant: {s.plant_code} -> Target: {s.action_parameters.get('target_plant_code')} ({s.action_parameters.get('cluster_zone')})")
            print(f"  Current Delay: {s.action_parameters.get('current_plant_delay_mins')}m | Alt Delay: {s.action_parameters.get('alternative_plant_delay_mins')}m | Net Reduction: -{s.action_parameters.get('predicted_delay_reduction_mins')}m")
            print(f"  Evidence: {s.dispatcher_notes}\n")

if __name__ == "__main__":
    asyncio.run(main())
