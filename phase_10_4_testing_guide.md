# Phase 10.4 Testing & Verification Guide

This guide describes how to execute the 22-test certification suite for WS-10.4 Automated Candidate Evaluation & Phase 7.3 Promotion-Gate Integration, as well as the full WS-10 regression suite.

---

## 1. Running the WS-10.4 Certification Test Suite

To run the dedicated 22-requirement WS-10.4 test suite inside the WSL environment:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_4_automated_candidate_evaluation.py -v
```

Expected Output:
```
collected 22 items
app/modules/operational_intelligence/tests/test_ws_10_4_automated_candidate_evaluation.py::test_ws_10_4_01_candidate_discovery PASSED
...
app/modules/operational_intelligence/tests/test_ws_10_4_automated_candidate_evaluation.py::test_ws_10_4_22_performance_benchmark PASSED

================ 22 passed in 566.33s ================
```

---

## 2. Running Full WS-10 Regression Matrix

To verify that all frozen WS-10 workstreams (10.1, 10.2, 10.3, 10.4) remain 100% passed and compatible:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest \
  app/modules/operational_intelligence/tests/test_ws_10_1_erp_ml_lifecycle_trigger.py \
  app/modules/operational_intelligence/tests/test_ws_10_2_feature_dataset_builder.py \
  app/modules/operational_intelligence/tests/test_ws_10_3_automated_candidate_training.py \
  app/modules/operational_intelligence/tests/test_ws_10_4_automated_candidate_evaluation.py
```

Regression Results Breakdown:
- `test_ws_10_1_erp_ml_lifecycle_trigger.py`: **11 PASSED**
- `test_ws_10_2_feature_dataset_builder.py`: **13 PASSED**
- `test_ws_10_3_automated_candidate_training.py`: **12 PASSED**
- `test_ws_10_4_automated_candidate_evaluation.py`: **22 PASSED**
- **TOTAL WS-10 REGRESSION SUITE**: **58 PASSED out of 58 (100% PASS RATE)**

---

## 3. Real Production Database State Safety Check

Execute the following SQL queries to confirm production database boundaries remain untouched:

```sql
-- 1. Confirm PROMOTED count is 0
SELECT COUNT(*) FROM ml_model_versions WHERE lifecycle_status = 'PROMOTED';
-- Expected Result: 0

-- 2. Confirm REJECTED count is preserved
SELECT COUNT(*) FROM ml_model_versions WHERE lifecycle_status = 'REJECTED';
-- Expected Result: 4

-- 3. Confirm prediction snapshots count is 0
SELECT COUNT(*) FROM ml_prediction_snapshots;
-- Expected Result: 0
```

---

## 4. Summary of 22 Certification Test Scenarios

| Test Function Name | Certification Requirement | Expected Result | Verified |
| :--- | :--- | :--- | :--- |
| `test_ws_10_4_01_candidate_discovery` | Candidate Discovery | Discovers `PENDING_EVALUATION` candidates | ✅ PASS |
| `test_ws_10_4_02_dataset_resolution` | Dataset Resolution | Resolves dataset from immutable registry | ✅ PASS |
| `test_ws_10_4_03_featureset_v1_compatibility` | FeatureSetV1 Compatibility | Rejects non-matching feature set versions | ✅ PASS |
| `test_ws_10_4_04_artifact_sha_verification` | Artifact Checksum Verification | Re-calculates SHA-256 before evaluation | ✅ PASS |
| `test_ws_10_4_05_holdout_test_only_evaluation` | Holdout Partition Isolation | Evaluates strictly on `HOLDOUT_TEST` records | ✅ PASS |
| `test_ws_10_4_06_no_holdout_preprocessing_fit` | No Preprocessor Refit | Preprocessor uses pre-fit transform | ✅ PASS |
| `test_ws_10_4_07_all_four_model_families` | All 4 Model Families | Evaluates delay, turnaround, sla, plant_risk | ✅ PASS |
| `test_ws_10_4_08_canonical_phase73_threshold_reuse` | Phase 7.3 Gate Reuse | Consumes `PROMOTION_GATE_THRESHOLDS` | ✅ PASS |
| `test_ws_10_4_09_passing_candidate_promotion_eligible` | PASS Candidate State | Decision becomes `PROMOTION_ELIGIBLE` | ✅ PASS |
| `test_ws_10_4_10_failing_candidate_rejection_state` | FAIL Candidate State | Decision and status become `REJECTED` | ✅ PASS |
| `test_ws_10_4_11_no_automatic_promotion` | Non-Promotion Boundary | `PROMOTED` count remains 0 | ✅ PASS |
| `test_ws_10_4_12_zero_prediction_snapshots` | Zero Prediction Snapshots | Zero snapshots created | ✅ PASS |
| `test_ws_10_4_13_artifact_mutation_detection` | Artifact Mutation Detection | Rejects with `ARTIFACT_MUTATION_DETECTED` | ✅ PASS |
| `test_ws_10_4_14_missing_artifact_rejection` | Missing Artifact | Rejects with `MISSING_ARTIFACT` | ✅ PASS |
| `test_ws_10_4_15_missing_dataset_rejection` | Missing Dataset | Rejects with `MISSING_DATASET` | ✅ PASS |
| `test_ws_10_4_16_empty_holdout_rejection` | Empty Holdout Partition | Rejects with `EMPTY_HOLDOUT` | ✅ PASS |
| `test_ws_10_4_17_concurrent_evaluator_protection` | Concurrency Locking | `SKIP LOCKED` prevents duplicate claims | ✅ PASS |
| `test_ws_10_4_18_duplicate_evaluation_idempotency` | Idempotency | Re-evaluating candidate yields identical decision | ✅ PASS |
| `test_ws_10_4_19_worker_restart_and_recovery` | Restart Recovery | Resumes evaluation on claimed candidate | ✅ PASS |
| `test_ws_10_4_20_audit_lineage_persistence` | Audit Lineage Persistence | Appends `MLModelAuditEvent` records | ✅ PASS |
| `test_ws_10_4_21_deterministic_evaluation` | Determinism | Identical metrics across evaluation runs | ✅ PASS |
| `test_ws_10_4_22_performance_benchmark` | Performance Benchmark | Evaluates 4 candidate models within SLO limit | ✅ PASS |
