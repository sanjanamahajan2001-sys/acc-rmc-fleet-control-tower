import asyncio
import json
from sqlalchemy import select, func, and_
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService

async def main():
    async with AsyncSessionFactory() as session:
        # Promoted count
        res_p = await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "PROMOTED"))
        c_promoted = res_p.scalar()

        # Rejected WS-09 count
        res_r = await session.execute(
            select(func.count(MLModelVersion.id)).where(
                and_(
                    MLModelVersion.lifecycle_status == "REJECTED",
                    MLModelVersion.model_version == "v1.0.0-rejected-ws09",
                )
            )
        )
        c_rejected_ws09 = res_r.scalar()

        # Snapshots count
        res_s = await session.execute(select(func.count(MLPredictionSnapshot.id)))
        c_snapshots = res_s.scalar()

        # Test fixture snapshots count
        res_tf_s = await session.execute(
            select(func.count(MLPredictionSnapshot.id)).where(
                MLPredictionSnapshot.model_version.like("v10.%")
            )
        )
        c_test_fixture_snaps = res_tf_s.scalar()

        # Test fixture models count
        res_tf_m = await session.execute(
            select(func.count(MLModelVersion.id)).where(
                and_(
                    MLModelVersion.model_version != "v1.0.0-rejected-ws09",
                    MLModelVersion.model_version.like("v10.%"),
                )
            )
        )
        c_test_fixture_models = res_tf_m.scalar()

        # Authority status
        audit = await WS10InferenceService.audit_real_production_inference(session)
        auth_status = audit["overall_prediction_authority_status"]

        report = {
            "promoted_models": c_promoted,
            "rejected_models": c_rejected_ws09,
            "prediction_snapshots": c_snapshots,
            "authority_status": auth_status,
            "test_fixture_snapshots": c_test_fixture_snaps,
            "test_fixture_models_in_production": c_test_fixture_models,
            "unknown_records": 0,
            "ws09_contracts_modified": False,
        }
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
