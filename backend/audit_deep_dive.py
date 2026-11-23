import asyncio
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionFactory
from app.modules.erp.models import Dispatch, Plant, Customer
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.services.predictive_telemetry_service import PredictiveTelemetryService
from app.modules.operational_intelligence.services.cost_exposure_service import OperationalCostExposureService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

async def main():
    async with AsyncSessionFactory() as session:
        # 1. Total Dispatches in DB
        tot_disp = (await session.execute(select(func.count(Dispatch.id)))).scalar()
        print("TOTAL DISPATCHES IN DB:", tot_disp)

        # 2. Total Snapshots in DB
        tot_snaps = (await session.execute(select(func.count(MLPredictionSnapshot.id)))).scalar()
        print("TOTAL SNAPSHOTS IN DB:", tot_snaps)

        # 3. Model Registry Versions
        models = (await session.execute(select(MLModelVersion))).scalars().all()
        print("MODEL VERSIONS IN DB:")
        for m in models:
            print(f"  - {m.model_name}: version={m.model_version}, lifecycle_status={m.lifecycle_status}, decision={m.evaluation_decision}")

        # 4. Telemetry
        tele = await PredictiveTelemetryService.get_telemetry(session)
        print("TELEMETRY AUTHORITY:", tele.production_authority, "COUNT:", tele.authoritative_model_count)
        print("TELEMETRY STATUS MAP:", tele.authority_status)

        # 5. ALL PLANTS Scope Cost Exposure
        params_all = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        res_all = await OperationalCostExposureService.get_cost_exposure(session, params_all)
        print("ALL SCOPE: Realized=", res_all.summary.realized_cost_exposure_inr, "Predicted=", res_all.summary.predicted_cost_exposure_inr, "Version=", res_all.provenance.model_version)

        # 6. ACC_NESSAI Scope Cost Exposure
        params_nessai = DashboardFilterParams(plant_id="ACC_NESSAI", customer_id="ALL", dataset_type="ALL")
        res_nessai = await OperationalCostExposureService.get_cost_exposure(session, params_nessai)
        print("ACC_NESSAI SCOPE: Realized=", res_nessai.summary.realized_cost_exposure_inr, "Predicted=", res_nessai.summary.predicted_cost_exposure_inr)

        # 7. Plants Breakdown
        plants = (await session.execute(select(Plant).where(Plant.is_deleted == False))).scalars().all()
        for p in plants:
            params_p = DashboardFilterParams(plant_id=p.code, customer_id="ALL", dataset_type="ALL")
            res_p = await OperationalCostExposureService.get_cost_exposure(session, params_p)
            disp_p = (await session.execute(select(func.count(Dispatch.id)).where(Dispatch.plant_id == p.id))).scalar()
            snap_p = (await session.execute(select(func.count(MLPredictionSnapshot.id)).where(MLPredictionSnapshot.plant_code == p.code))).scalar()
            print(f"PLANT {p.code} ({p.name}): dispatches={disp_p}, snapshots={snap_p}, Realized={res_p.summary.realized_cost_exposure_inr}, Predicted={res_p.summary.predicted_cost_exposure_inr}")

if __name__ == "__main__":
    asyncio.run(main())
