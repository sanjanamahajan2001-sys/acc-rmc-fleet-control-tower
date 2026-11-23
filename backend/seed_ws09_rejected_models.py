import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.modules.operational_intelligence.tests.conftest import TestAsyncSessionFactory
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent

REJECTED_MODELS = [
    {
        "model_name": "delay_regressor",
        "model_category": "Regression",
        "model_version": "v1.0.0-rejected-ws09",
        "algorithm": "RandomForestRegressor",
        "target_name": "predicted_delay_mins",
        "feature_set_version": "FeatureSetV1",
        "training_dataset_id": "DS-HISTORICAL-WS09",
        "artifact_path": "/tmp/dummy_delay.joblib",
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "artifact_size_bytes": 100,
        "training_timestamp": datetime.now(timezone.utc),
        "lifecycle_status": "REJECTED",
        "evaluation_decision": "REJECTED",
        "rejection_reasons": ["GATE_THRESHOLD_FAILED: R2 score below Phase 7.3 threshold"],
    },
    {
        "model_name": "turnaround_regressor",
        "model_category": "Regression",
        "model_version": "v1.0.0-rejected-ws09",
        "algorithm": "RandomForestRegressor",
        "target_name": "predicted_avg_turnaround_mins",
        "feature_set_version": "FeatureSetV1",
        "training_dataset_id": "DS-HISTORICAL-WS09",
        "artifact_path": "/tmp/dummy_turnaround.joblib",
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "artifact_size_bytes": 100,
        "training_timestamp": datetime.now(timezone.utc),
        "lifecycle_status": "REJECTED",
        "evaluation_decision": "REJECTED",
        "rejection_reasons": ["GATE_THRESHOLD_FAILED: MAE above Phase 7.3 threshold"],
    },
    {
        "model_name": "sla_breach_classifier",
        "model_category": "Classification",
        "model_version": "v1.0.0-rejected-ws09",
        "algorithm": "RandomForestClassifier",
        "target_name": "predicted_sla_breach_target",
        "feature_set_version": "FeatureSetV1",
        "training_dataset_id": "DS-HISTORICAL-WS09",
        "artifact_path": "/tmp/dummy_sla.joblib",
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "artifact_size_bytes": 100,
        "training_timestamp": datetime.now(timezone.utc),
        "lifecycle_status": "REJECTED",
        "evaluation_decision": "REJECTED",
        "rejection_reasons": ["GATE_THRESHOLD_FAILED: ROC-AUC below Phase 7.3 threshold"],
    },
    {
        "model_name": "plant_risk_classifier",
        "model_category": "Classification",
        "model_version": "v1.0.0-rejected-ws09",
        "algorithm": "RandomForestClassifier",
        "target_name": "predicted_plant_congestion_target",
        "feature_set_version": "FeatureSetV1",
        "training_dataset_id": "DS-HISTORICAL-WS09",
        "artifact_path": "/tmp/dummy_risk.joblib",
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "artifact_size_bytes": 100,
        "training_timestamp": datetime.now(timezone.utc),
        "lifecycle_status": "REJECTED",
        "evaluation_decision": "REJECTED",
        "rejection_reasons": ["GATE_THRESHOLD_FAILED: F1 score below Phase 7.3 threshold"],
    },
]

async def seed():
    async with TestAsyncSessionFactory() as session:
        # Clear any lingering test promoted models
        stmt_prom = select(MLModelVersion).where(MLModelVersion.lifecycle_status == "PROMOTED")
        res_prom = await session.execute(stmt_prom)
        for pm in res_prom.scalars().all():
            pm.lifecycle_status = "RETIRED"

        for item in REJECTED_MODELS:
            stmt = select(MLModelVersion).where(
                MLModelVersion.model_name == item["model_name"],
                MLModelVersion.model_version == item["model_version"],
            )
            res = await session.execute(stmt)
            mv = res.scalars().first()
            if not mv:
                mv = MLModelVersion(**item)
                session.add(mv)
                await session.flush()

            # Ensure audit event exists
            stmt_a = select(MLModelAuditEvent).where(MLModelAuditEvent.model_version_id == mv.id)
            res_a = await session.execute(stmt_a)
            if not res_a.scalars().first():
                ae = MLModelAuditEvent(
                    model_version_id=mv.id,
                    model_name=mv.model_name,
                    model_version=mv.model_version,
                    event_type="MODEL_REJECTED",
                    previous_status="TRAINED_CANDIDATE",
                    new_status="REJECTED",
                    artifact_sha256=mv.artifact_sha256,
                    decision_details={"reason": "WS-09 Phase 7.3 baseline rejection"},
                )
                session.add(ae)

        await session.commit()
        print("[SEED] 4 WS-09 historical REJECTED models and audit events seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
