# Phase 10.4 Automated Candidate Evaluation & Phase 7.3 Promotion-Gate Integration Walkthrough

## Executive Summary & Final Certification Decision
WS-10.4 establishes the automated candidate evaluation subsystem connecting candidate models produced by WS-10.3 (`TRAINED_CANDIDATE`) to the authoritative Phase 7.3 Model Evaluation & Promotion Gate.

The certification gaps identified in preflight auditing have been fully remediated and certified:
- **Test Count Consistency**: Pytest collects **EXACTLY 22 items** in `test_ws_10_4_automated_candidate_evaluation.py`, matching the 22 required verification scenarios 1-to-1. All 22 tests pass cleanly (100% PASS RATE).
- **Phase 7.3 Gate Authority Reuse**: WS-10.4 consumes Phase 7.3 promotion gate thresholds directly from the canonical source (`app.modules.operational_intelligence.ml.evaluator.PROMOTION_GATE_THRESHOLDS`) without duplicating threshold constants.

---

## 1. Architecture & Authority Flow

```
[TRAINED_CANDIDATE Models]
          │
          ▼
WS10CandidateEvaluationService
  ├── 1. Claim Candidate (SELECT ... FOR UPDATE SKIP LOCKED)
  ├── 2. Verify Artifact SHA-256 Checksum
  ├── 3. Extract Immutable HOLDOUT_TEST Partition Records
  ├── 4. Load Scikit-Learn Model Estimator & Align Feature Matrix
  └── 5. Delegate to Authoritative Phase 7.3 Promotion Gate
          │
          ▼
Phase 7.3 Promotion Gate Authority (evaluator.py)
  ├── Canonical Thresholds (PROMOTION_GATE_THRESHOLDS)
  └── Metric Evaluation Engine (Regression & Classification)
          │
          ▼
     ┌────┴─────────────────────────────┐
     ▼                                  ▼
[Overall Gate PASSED]          [Overall Gate FAILED]
     │                                  │
     ▼                                  ▼
evaluation_decision:           evaluation_decision:
  PROMOTION_ELIGIBLE             REJECTED
lifecycle_status:              lifecycle_status:
  TRAINED_CANDIDATE              REJECTED
(PROMOTED remains 0)
```

---

## 2. Exact Phase 7.3 Authority Source & Canonical Thresholds

- **Authority Source File**: `app/modules/operational_intelligence/ml/evaluator.py`
- **Authority Class**: `Phase73PromotionGateEvaluator`
- **Canonical Threshold Dictionary**: `PROMOTION_GATE_THRESHOLDS`

### Canonical Promotion Threshold Values
1. **`delay_regressor`** (Regression):
   - `r2` ≥ `0.70`
   - `mae` ≤ `10.0`
   - `rmse` ≤ `15.0`
2. **`turnaround_regressor`** (Regression):
   - `r2` ≥ `0.70`
   - `mae` ≤ `8.0`
   - `rmse` ≤ `12.0`
3. **`sla_breach_classifier`** (Classification):
   - `roc_auc` ≥ `0.75`
   - `f1` ≥ `0.70`
   - `precision` ≥ `0.65`
   - `recall` ≥ `0.65`
4. **`plant_risk_classifier`** (Classification):
   - `roc_auc` ≥ `0.75`
   - `f1` ≥ `0.70`
   - `precision` ≥ `0.65`
   - `recall` ≥ `0.65`

---

## 3. Four Model Family Metric Mappings

| Model Family | Model Category | Primary Target Column | Computed Evaluation Metrics |
| :--- | :--- | :--- | :--- |
| `delay_regressor` | Regression | `predicted_delay_mins` | R², MAE, RMSE |
| `turnaround_regressor` | Regression | `predicted_avg_turnaround_mins` | R², MAE, RMSE |
| `sla_breach_classifier` | Classification | `predicted_sla_breach_target` | ROC-AUC, F1, Precision, Recall |
| `plant_risk_classifier` | Classification | `predicted_plant_congestion_target` | ROC-AUC, F1, Precision, Recall |

---

## 4. Holdout Isolation & Artifact Integrity
- **Holdout Isolation**: Evaluation is performed **strictly** on the `HOLDOUT_TEST` dataset partition. The feature preprocessor is **NEVER** refit on holdout data during evaluation; it uses pre-fit transformation matrices.
- **Artifact SHA-256 Verification**: Before deserializing `.joblib` model artifacts, the evaluator computes the file's SHA-256 hash on disk and compares it to `MLModelVersion.artifact_sha256`. Any mismatch immediately halts evaluation and marks the candidate `REJECTED` with reason `ARTIFACT_MUTATION_DETECTED`.

---

## 5. Lifecycle State Machine & Rejection Semantics

| Initial Lifecycle Status | Initial Decision | Evaluation Result | New Lifecycle Status | New Decision |
| :--- | :--- | :--- | :--- | :--- |
| `TRAINED_CANDIDATE` | `PENDING_EVALUATION` | **PASS** (All Gates) | `TRAINED_CANDIDATE` | `PROMOTION_ELIGIBLE` |
| `TRAINED_CANDIDATE` | `PENDING_EVALUATION` | **FAIL** (Any Gate) | `REJECTED` | `REJECTED` |
| `TRAINED_CANDIDATE` | `PENDING_EVALUATION` | **MUTATION DETECTED** | `REJECTED` | `REJECTED` |
| `TRAINED_CANDIDATE` | `PENDING_EVALUATION` | **MISSING ARTIFACT** | `REJECTED` | `REJECTED` |
| `TRAINED_CANDIDATE` | `PENDING_EVALUATION` | **EMPTY HOLDOUT** | `REJECTED` | `REJECTED` |

*Note: Evaluation PASS does NOT automatically promote a model. Promoted count remains strictly 0.*

---

## 6. Concurrency, Recovery & Idempotency
- **Concurrency Locking**: `MLModelRegistryRepository.claim_next_pending_candidate()` uses PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`, allowing safe multi-worker evaluation without double-claiming.
- **Restart Recovery**: Workers safely resume claimed candidates upon restart without corrupting state.
- **Idempotency**: Re-evaluating an already evaluated candidate returns the existing decision idempotently without duplicate audit side-effects.

---

## 7. Performance Evidence

- **Single Candidate Model Evaluation Latency**: ~`1.2` seconds (including SHA-256 computation, dataset extraction, model deserialization, holdout inference, metric calculation, DB update, and audit logging).
- **Entire Test Suite Runtime (22 Tests)**: `566.33` seconds (~9.4 minutes in local WSL environment running end-to-end PostgreSQL transactions and model fitting).
- **SLO Baseline Assertion**: `assert duration < 120.0s` for evaluation of all 4 model families on an existing dataset.

---

## 8. Real PostgreSQL Production Authority Audit

| Production Metric | Required Authority State | Actual Database State | Verification Status |
| :--- | :--- | :--- | :--- |
| **`PROMOTED` Models** | `0` | `0` | ✅ PASSED |
| **`REJECTED` Models** | `4` frozen WS-09 candidates | `4` | ✅ PASSED |
| **`PREDICTION AUTHORITY`** | `NOT_CONFIGURED` | `NOT_CONFIGURED` | ✅ PASSED |
| **`PREDICTION SNAPSHOTS`** | `0` | `0` | ✅ PASSED |

---

## 9. 22 Certification Test Method Mapping

Pytest Collected Items: **EXACTLY 22 items in `test_ws_10_4_automated_candidate_evaluation.py`**.

| Scenario # | Requirement Description | Test Function Name | Pytest Result |
| :--- | :--- | :--- | :--- |
| 1 | Candidate Discovery | `test_ws_10_4_01_candidate_discovery` | ✅ PASSED |
| 2 | Dataset Resolution | `test_ws_10_4_02_dataset_resolution` | ✅ PASSED |
| 3 | FeatureSetV1 Compatibility | `test_ws_10_4_03_featureset_v1_compatibility` | ✅ PASSED |
| 4 | Artifact SHA Verification | `test_ws_10_4_04_artifact_sha_verification` | ✅ PASSED |
| 5 | Holdout Partition Isolation | `test_ws_10_4_05_holdout_test_only_evaluation` | ✅ PASSED |
| 6 | No Preprocessor Refit on Holdout | `test_ws_10_4_06_no_holdout_preprocessing_fit` | ✅ PASSED |
| 7 | All 4 Model Families Evaluated | `test_ws_10_4_07_all_four_model_families` | ✅ PASSED |
| 8 | Canonical Phase 7.3 Threshold Reuse | `test_ws_10_4_08_canonical_phase73_threshold_reuse` | ✅ PASSED |
| 9 | Passing Candidate -> `PROMOTION_ELIGIBLE` | `test_ws_10_4_09_passing_candidate_promotion_eligible` | ✅ PASSED |
| 10 | Failing Candidate -> `REJECTED` | `test_ws_10_4_10_failing_candidate_rejection_state` | ✅ PASSED |
| 11 | No Automatic Promotion Boundary | `test_ws_10_4_11_no_automatic_promotion` | ✅ PASSED |
| 12 | Zero Prediction Snapshots | `test_ws_10_4_12_zero_prediction_snapshots` | ✅ PASSED |
| 13 | Artifact Mutation Detection | `test_ws_10_4_13_artifact_mutation_detection` | ✅ PASSED |
| 14 | Missing Artifact Handling | `test_ws_10_4_14_missing_artifact_rejection` | ✅ PASSED |
| 15 | Missing Dataset Handling | `test_ws_10_4_15_missing_dataset_rejection` | ✅ PASSED |
| 16 | Empty Holdout Handling | `test_ws_10_4_16_empty_holdout_rejection` | ✅ PASSED |
| 17 | Concurrent Evaluator Protection | `test_ws_10_4_17_concurrent_evaluator_protection` | ✅ PASSED |
| 18 | Duplicate Evaluation Idempotency | `test_ws_10_4_18_duplicate_evaluation_idempotency` | ✅ PASSED |
| 19 | Worker Restart and Recovery | `test_ws_10_4_19_worker_restart_and_recovery` | ✅ PASSED |
| 20 | Audit Lineage Persistence | `test_ws_10_4_20_audit_lineage_persistence` | ✅ PASSED |
| 21 | Deterministic Metric Calculation | `test_ws_10_4_21_deterministic_evaluation` | ✅ PASSED |
| 22 | Performance Benchmark Execution | `test_ws_10_4_22_performance_benchmark` | ✅ PASSED |
