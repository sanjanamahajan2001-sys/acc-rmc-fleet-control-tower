# WS-10.6 Testing & Verification Guide

This guide describes how to execute the 24-test certification suite for WS-10.6 Authoritative Predictive Inference & Prediction Snapshot Generation, as well as the full WS-10 master regression matrix.

---

## 1. Running the WS-10.6 Certification Test Suite

To run the dedicated 24-requirement WS-10.6 test suite inside the WSL environment:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_6_authoritative_inference_snapshots.py -v
```

Expected Output:
```
collected 24 items
app/modules/operational_intelligence/tests/test_ws_10_6_authoritative_inference_snapshots.py::test_ws_10_6_01_promoted_model_resolution PASSED
...
app/modules/operational_intelligence/tests/test_ws_10_6_authoritative_inference_snapshots.py::test_ws_10_6_24_performance_benchmark PASSED

====================== 24 passed in 3.79s ======================
```

---

## 2. Running Full WS-10 Master Regression Matrix

To verify that all frozen WS-10 workstreams (10.1 through 10.6) remain 100% passed and compatible:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest \
  app/modules/operational_intelligence/tests/test_ws_10_1_erp_ml_lifecycle_trigger.py \
  app/modules/operational_intelligence/tests/test_ws_10_2_feature_dataset_builder.py \
  app/modules/operational_intelligence/tests/test_ws_10_3_automated_candidate_training.py \
  app/modules/operational_intelligence/tests/test_ws_10_4_automated_candidate_evaluation.py \
  app/modules/operational_intelligence/tests/test_ws_10_5_controlled_model_promotion.py \
  app/modules/operational_intelligence/tests/test_ws_10_6_authoritative_inference_snapshots.py
```

Regression Results Breakdown:
- `test_ws_10_1_erp_ml_lifecycle_trigger.py`: **11 PASSED**
- `test_ws_10_2_feature_dataset_builder.py`: **13 PASSED**
- `test_ws_10_3_automated_candidate_training.py`: **12 PASSED**
- `test_ws_10_4_automated_candidate_evaluation.py`: **22 PASSED**
- `test_ws_10_5_controlled_model_promotion.py`: **18 PASSED**
- `test_ws_10_6_authoritative_inference_snapshots.py`: **24 PASSED**
- **TOTAL WS-10 MASTER REGRESSION SUITE**: **100 PASSED out of 100 (100% PASS RATE)**

---

## 3. Real Production Database Audit Command

Execute the real PostgreSQL production audit script:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
python3 -c "
import asyncio, json
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService

async def main():
    async with AsyncSessionFactory() as session:
        report = await WS10InferenceService.audit_real_production_inference(session)
        print(json.dumps(report, indent=2))

asyncio.run(main())
"
```

Expected Output:
```json
{
  "timestamp": "2026-08-18T04:41:28.798809+00:00",
  "total_models_count": 295,
  "promoted_models_count": 0,
  "snapshots_count": 30,
  "overall_prediction_authority_status": "NOT_CONFIGURED",
  "audit_message": "No active PROMOTED model versions configured. Prediction authority remains NOT_CONFIGURED."
}
```

---

## 4. Summary of 24 Certification Test Scenarios

| Test Function Name | Certification Requirement | Expected Result | Verified |
| :--- | :--- | :--- | :--- |
| `test_ws_10_6_01_promoted_model_resolution` | Promoted Resolution | Resolves `PROMOTED` model version | ✅ PASS |
| `test_ws_10_6_02_zero_promoted_model_safety` | Zero Promoted Safety | Returns `None` when 0 promoted models exist | ✅ PASS |
| `test_ws_10_6_03_rejected_model_protection` | Rejected Protection | Blocks inference for `REJECTED` candidate | ✅ PASS |
| `test_ws_10_6_04_trained_candidate_protection` | Candidate Protection | Blocks inference for `TRAINED_CANDIDATE` | ✅ PASS |
| `test_ws_10_6_05_retired_model_protection` | Retirement Protection | Blocks inference for `RETIRED` model | ✅ PASS |
| `test_ws_10_6_06_artifact_sha_verification` | SHA Verification | Checks SHA-256 before loading pipeline | ✅ PASS |
| `test_ws_10_6_07_featureset_v1_feature_extraction` | Feature Extraction | Extracts FeatureSetV1 feature vector | ✅ PASS |
| `test_ws_10_6_08_inference_anti_leakage` | Anti-Leakage Guard | Rejects target/post-outcome fields | ✅ PASS |
| `test_ws_10_6_09_real_dispatch_inference` | Real Dispatch Inference | Executes scikit-learn model prediction | ✅ PASS |
| `test_ws_10_6_10_prediction_output_validation` | Output Validation | Validates prediction outputs structure | ✅ PASS |
| `test_ws_10_6_11_snapshot_persistence` | Snapshot Persistence | Persists `MLPredictionSnapshot` in DB | ✅ PASS |
| `test_ws_10_6_12_snapshot_lineage_completeness` | Lineage Completeness | Includes full lineage metadata fields | ✅ PASS |
| `test_ws_10_6_13_idempotency` | Idempotency | Matching idempotency key returns existing | ✅ PASS |
| `test_ws_10_6_14_concurrent_inference_protection` | Concurrent Protection | Handles concurrent requests safely | ✅ PASS |
| `test_ws_10_6_15_duplicate_snapshot_protection` | Duplicate Protection | Prevents duplicate snapshot insertion | ✅ PASS |
| `test_ws_10_6_16_transaction_rollback` | Rollback Safety | Rollback on failure preserves DB state | ✅ PASS |
| `test_ws_10_6_17_zero_fake_prediction_protection` | Zero Fake Predictions | Zero snapshots created when PROMOTED = 0 | ✅ PASS |
| `test_ws_10_6_18_not_configured_state` | NOT_CONFIGURED State | Verifies `NOT_CONFIGURED` state | ✅ PASS |
| `test_ws_10_6_19_no_data_state` | NO_DATA State | Verifies `NO_DATA` state | ✅ PASS |
| `test_ws_10_6_20_authoritative_state` | AUTHORITATIVE State | Verifies `AUTHORITATIVE` state | ✅ PASS |
| `test_ws_10_6_21_historical_snapshot_preservation` | Historical Preservation | Preserves snapshots after model retirement | ✅ PASS |
| `test_ws_10_6_22_global_filter_compatibility` | Global Filters | Matches global filter queries | ✅ PASS |
| `test_ws_10_6_23_four_model_family_output_verification` | Four Model Families | Verifies outputs for 4 model families | ✅ PASS |
| `test_ws_10_6_24_performance_benchmark` | Performance Benchmark | Latency < 100ms per dispatch | ✅ PASS |
