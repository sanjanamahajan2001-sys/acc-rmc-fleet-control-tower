"""
Script to test API financial exposure calculation directly from backend service.
"""

import asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService, DashboardFilterParams

async def check():
    async with AsyncSessionFactory() as session:
        params = DashboardFilterParams()
        res = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
        
        print(f"==================================================")
        print(f"PREDICTIVE OVERVIEW CALCULATION STATUS: {res.calculation_status}")
        print(f"TOTAL SNAPSHOTS RETURNED: {len(res.snapshots)}")
        print(f"==================================================")
        
        for idx, snap in enumerate(res.snapshots[:3]):
            print(f"\n--- SNAPSHOT #{idx+1} ({snap.model_name}) ---")
            print(f"  Dispatch Code      : {snap.dispatch_code}")
            print(f"  Predicted Value    : {snap.predicted_value}")
            print(f"  Delay Cost Risk    : ₹{snap.financial_exposure_inr}")
            print(f"  SLA Penalty Risk   : ₹{snap.sla_penalty_risk_inr}")
            print(f"  Plant Risk         : ₹{snap.plant_congestion_risk_inr}")
            print(f"  Idle Queue Cost    : ₹{snap.idle_queue_cost_inr}")
            print(f"  Total Risk         : ₹{snap.total_financial_risk_inr}")
            print(f"  Lineage Status     : {snap.calculation_lineage.get('calculation_status') if snap.calculation_lineage else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(check())
