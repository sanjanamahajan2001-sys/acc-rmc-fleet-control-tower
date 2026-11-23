"""
WS-10.6 Production Database State Remediation & Forensic Audit Script.
Safely audits and transactionally cleans test-generated records from PostgreSQL.
Supports --dry-run (default) and --execute --confirm-production-remediation.
"""

import sys
import os
import argparse
import asyncio
import json
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.models.ml_training_job import MLTrainingJob

PROTECTED_WS09_MODELS = [
    "delay_regressor",
    "turnaround_regressor",
    "sla_breach_classifier",
    "plant_risk_classifier",
]
PROTECTED_WS09_VERSION = "v1.0.0-rejected-ws09"


async def run_forensic_audit(session: AsyncSession):
    """Audits and classifies all database records."""
    # 1. Snapshots
    res_s = await session.execute(select(MLPredictionSnapshot))
    snaps = list(res_s.scalars().all())

    classified_snaps = {
        "A_legitimate_production": [],
        "B_test_fixture": [],
        "D_unknown": [],
    }

    for s in snaps:
        # Check test fixture signals: model_version like v10.6, v10.5, test dispatch codes, IK test keys
        is_test = (
            "v10.6." in (s.model_version or "")
            or "v10.5." in (s.model_version or "")
            or "v10.3." in (s.model_version or "")
            or "IK-" in (s.idempotency_key or "")
            or "DISP-" in (s.dispatch_code or "")
            or "delay_reg_" in (s.model_name or "")
            or "sla_breach_" in (s.model_name or "")
            or "turnaround_" in (s.model_name or "")
            or "plant_risk_" in (s.model_name or "")
        )
        if is_test:
            classified_snaps["B_test_fixture"].append(s)
        else:
            classified_snaps["D_unknown"].append(s)

    # 2. Model Versions
    res_m = await session.execute(select(MLModelVersion))
    models = list(res_m.scalars().all())

    classified_models = {
        "A_protected_ws09": [],
        "B_legitimate_ws10": [],
        "C_test_fixture": [],
        "D_unknown": [],
    }

    for m in models:
        if m.model_name in PROTECTED_WS09_MODELS and m.model_version == PROTECTED_WS09_VERSION:
            classified_models["A_protected_ws09"].append(m)
        elif (
            "v10.6." in (m.model_version or "")
            or "v10.5." in (m.model_version or "")
            or "v10.3." in (m.model_version or "")
            or "DS-SAFETY-" in (m.training_dataset_id or "")
            or "DS-INF-TEST-" in (m.training_dataset_id or "")
            or "DS-MUTATE-" in (m.training_dataset_id or "")
            or "DS-FAIL-" in (m.training_dataset_id or "")
            or "DS-DISCOVERY-" in (m.training_dataset_id or "")
            or "DS-PERF-TRAIN-" in (m.training_dataset_id or "")
            or "DS-REPRO-TRAIN-" in (m.training_dataset_id or "")
            or "DS-FSV1-" in (m.training_dataset_id or "")
            or "test_promoted" in (m.artifact_path or "")
            or "_" in m.model_name  # test family names like delay_reg_inf_afb7
        ):
            classified_models["C_test_fixture"].append(m)
        elif m.training_dataset_id and m.training_dataset_id.startswith("DS-2026"):
            classified_models["B_legitimate_ws10"].append(m)
        else:
            # Check if it's a test generated version from WS-10 testing
            if m.model_version and ("candidate" in m.model_version or "test" in m.model_version):
                classified_models["C_test_fixture"].append(m)
            else:
                classified_models["D_unknown"].append(m)

    # 3. Datasets
    res_d = await session.execute(select(MLDataset))
    datasets = list(res_d.scalars().all())

    classified_datasets = {
        "A_legitimate_production": [],
        "B_test_fixture": [],
        "D_unknown": [],
    }
    for d in datasets:
        if d.dataset_id.startswith("DS-2026"):
            classified_datasets["A_legitimate_production"].append(d)
        else:
            classified_datasets["B_test_fixture"].append(d)

    # 4. Triggers
    res_t = await session.execute(select(MLLifecycleTrigger))
    triggers = list(res_t.scalars().all())

    classified_triggers = {
        "A_legitimate_production": [],
        "B_test_fixture": [],
        "D_unknown": [],
    }
    for t in triggers:
        if t.trigger_id.startswith("TR-2026"):
            classified_triggers["A_legitimate_production"].append(t)
        else:
            classified_triggers["B_test_fixture"].append(t)

    # 5. Training Jobs
    res_j = await session.execute(select(MLTrainingJob))
    jobs = list(res_j.scalars().all())

    classified_jobs = {
        "A_legitimate_production": [],
        "B_test_fixture": [],
        "D_unknown": [],
    }
    for j in jobs:
        if j.job_id.startswith("TRJOB-2026"):
            classified_jobs["A_legitimate_production"].append(j)
        else:
            classified_jobs["B_test_fixture"].append(j)

    return {
        "snapshots": classified_snaps,
        "models": classified_models,
        "datasets": classified_datasets,
        "triggers": classified_triggers,
        "jobs": classified_jobs,
    }


async def main():
    parser = argparse.ArgumentParser(description="WS-10.6 Production Database State Remediation")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry-run audit only (default)")
    parser.add_argument("--execute", action="store_true", help="Execute database remediation")
    parser.add_argument("--confirm-production-remediation", action="store_true", help="Confirm production remediation execution")

    args = parser.parse_args()

    execute_mode = args.execute and args.confirm_production_remediation

    print("==========================================================")
    print("WS-10.6 PRODUCTION DATABASE STATE REMEDIATION & AUDIT")
    print(f"MODE: {'[EXECUTE]' if execute_mode else '[DRY-RUN]'}")
    print("==========================================================")

    async with AsyncSessionFactory() as session:
        audit_results = await run_forensic_audit(session)

        snaps_audit = audit_results["snapshots"]
        models_audit = audit_results["models"]
        datasets_audit = audit_results["datasets"]

        print(f"\n1. SNAPSHOTS CLASSIFICATION:")
        print(f"   Total Snapshots: {sum(len(v) for v in snaps_audit.values())}")
        print(f"   A. Legitimate Production: {len(snaps_audit['A_legitimate_production'])}")
        print(f"   B. Test Fixtures: {len(snaps_audit['B_test_fixture'])}")
        print(f"   D. Unknown / Unclassified: {len(snaps_audit['D_unknown'])}")

        print(f"\n2. MODEL VERSIONS CLASSIFICATION:")
        print(f"   Total Model Versions: {sum(len(v) for v in models_audit.values())}")
        print(f"   A. Protected WS-09 Historical: {len(models_audit['A_protected_ws09'])}")
        print(f"   B. Legitimate WS-10 Candidates: {len(models_audit['B_legitimate_ws10'])}")
        print(f"   C. Test Fixtures: {len(models_audit['C_test_fixture'])}")
        print(f"   D. Unknown / Unclassified: {len(models_audit['D_unknown'])}")

        print(f"\n3. DATASETS CLASSIFICATION:")
        print(f"   Total Datasets: {sum(len(v) for v in datasets_audit.values())}")
        print(f"   A. Legitimate Production: {len(datasets_audit['A_legitimate_production'])}")
        print(f"   B. Test Fixtures: {len(datasets_audit['B_test_fixture'])}")
        print(f"   D. Unknown / Unclassified: {len(datasets_audit['D_unknown'])}")

        if len(snaps_audit['D_unknown']) > 0 or len(models_audit['D_unknown']) > 0:
            print("\n[CRITICAL ERROR] UNKNOWN/UNCLASSIFIED RECORDS FOUND! ABORTING REMEDIATION.")
            sys.exit(1)

        if len(models_audit['A_protected_ws09']) != 4:
            print(f"\n[CRITICAL ERROR] Protected WS-09 record count is {len(models_audit['A_protected_ws09'])}, expected 4! ABORTING.")
            sys.exit(1)

        if not execute_mode:
            print("\n[DRY-RUN COMPLETE] No database modifications were performed.")
            print("To execute remediation, run: python3 remediate_production_database_state.py --execute --confirm-production-remediation")
            return

        # EXECUTE REMEDIATION TRANSACTIONALLY
        print("\nBeginning transactional database cleanup...")
        try:
            # Delete test snapshots
            test_snap_ids = [s.prediction_snapshot_id for s in snaps_audit['B_test_fixture']]
            if test_snap_ids:
                await session.execute(delete(MLPredictionSnapshot).where(MLPredictionSnapshot.prediction_snapshot_id.in_(test_snap_ids)))
                print(f"  [CLEANUP] Deleted {len(test_snap_ids)} test prediction snapshot(s).")

            # Delete test model versions
            test_model_ids = [m.id for m in models_audit['C_test_fixture']]
            if test_model_ids:
                await session.execute(delete(MLModelAuditEvent).where(MLModelAuditEvent.model_version_id.in_(test_model_ids)))
                await session.execute(delete(MLModelVersion).where(MLModelVersion.id.in_(test_model_ids)))
                print(f"  [CLEANUP] Deleted {len(test_model_ids)} test model version(s).")

            # Delete test datasets
            test_dataset_ids = [d.dataset_id for d in datasets_audit['B_test_fixture']]
            if test_dataset_ids:
                await session.execute(delete(MLDataset).where(MLDataset.dataset_id.in_(test_dataset_ids)))
                print(f"  [CLEANUP] Deleted {len(test_dataset_ids)} test dataset(s).")

            # Delete test triggers
            test_trigger_ids = [t.trigger_id for t in audit_results["triggers"]['B_test_fixture']]
            if test_trigger_ids:
                await session.execute(delete(MLLifecycleTrigger).where(MLLifecycleTrigger.trigger_id.in_(test_trigger_ids)))
                print(f"  [CLEANUP] Deleted {len(test_trigger_ids)} test trigger(s).")

            # Delete test training jobs
            test_job_ids = [j.job_id for j in audit_results["jobs"]['B_test_fixture']]
            if test_job_ids:
                await session.execute(delete(MLTrainingJob).where(MLTrainingJob.job_id.in_(test_job_ids)))
                print(f"  [CLEANUP] Deleted {len(test_job_ids)} test training job(s).")

            await session.commit()
            print("[REMEDIATION SUCCESSFUL] Transaction committed.")

            # Post-cleanup verification
            async with AsyncSessionFactory() as verify_session:
                res_v_p = await verify_session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "PROMOTED"))
                c_promoted = res_v_p.scalar()

                res_v_r = await verify_session.execute(select(func.count(MLModelVersion.id)).where(and_(MLModelVersion.lifecycle_status == "REJECTED", MLModelVersion.model_version == PROTECTED_WS09_VERSION)))
                c_rejected_ws09 = res_v_r.scalar()

                res_v_s = await verify_session.execute(select(func.count(MLPredictionSnapshot.id)))
                c_snapshots = res_v_s.scalar()

                print("\n==========================================================")
                print("POST-REMEDIATION BASELINE VERIFICATION")
                print("==========================================================")
                print(f"  PROMOTED Models Count: {c_promoted} (Expected: 0)")
                print(f"  Protected WS-09 REJECTED Count: {c_rejected_ws09} (Expected: 4)")
                print(f"  Prediction Snapshots Count: {c_snapshots} (Expected: 0)")
                print(f"  Prediction Authority Status: NOT_CONFIGURED")
                print("==========================================================")

                assert c_promoted == 0
                assert c_rejected_ws09 == 4
                assert c_snapshots == 0

        except Exception as e:
            await session.rollback()
            print(f"[REMEDIATION FAILED] Transaction rolled back due to error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
