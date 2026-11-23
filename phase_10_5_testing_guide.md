# WS-10.5 Testing & Verification Guide

This guide describes how to execute the 18-test certification suite for WS-10.5 Controlled Legitimate Model Promotion & Production Authority Activation, as well as the full WS-10 regression matrix.

---

## 1. Running the WS-10.5 Certification Test Suite

To run the dedicated 18-requirement WS-10.5 test suite inside the WSL environment:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_5_controlled_model_promotion.py -v
```

Expected Output:
```
collected 18 items
app/modules/operational_intelligence/tests/test_ws_10_5_controlled_model_promotion.py::test_ws_10_5_01_eligible_candidate_discovery PASSED
...
app/modules/operational_intelligence/tests/test_ws_10_5_controlled_model_promotion.py::test_ws_10_5_18_production_state_safety PASSED

====================== 18 passed in 3.73s ======================
```

---

## 2. Running Full WS-10 Master Regression Matrix

To verify that all frozen WS-10 workstreams (10.1, 10.2, 10.3, 10.4, 10.5) remain 100% passed and compatible:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest \
  app/modules/operational_intelligence/tests/test_ws_10_1_erp_ml_lifecycle_trigger.py \
  app/modules/operational_intelligence/tests/test_ws_10_2_feature_dataset_builder.py \
  app/modules/operational_intelligence/tests/test_ws_10_3_automated_candidate_training.py \
  app/modules/operational_intelligence/tests/test_ws_10_4_automated_candidate_evaluation.py \
  app/modules/operational_intelligence/tests/test_ws_10_5_controlled_model_promotion.py
```

Regression Results Breakdown:
- `test_ws_10_1_erp_ml_lifecycle_trigger.py`: **11 PASSED**
- `test_ws_10_2_feature_dataset_builder.py`: **13 PASSED**
- `test_ws_10_3_automated_candidate_training.py`: **12 PASSED**
- `test_ws_10_4_automated_candidate_evaluation.py`: **22 PASSED**
- `test_ws_10_5_controlled_model_promotion.py`: **18 PASSED**
- **TOTAL WS-10 REGRESSION SUITE**: **76 PASSED out of 76 (100% PASS RATE)**

---

## 3. Real Production Database Audit Command

Execute the real PostgreSQL production audit script to verify candidate eligibility state:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
python3 -c "
import asyncio, json
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.services.promotion_service import WS10ModelPromotionService

async def main():
    async with AsyncSessionFactory() as session:
        report = await WS10ModelPromotionService.audit_real_production_candidate_eligibility(session)
        print(json.dumps(report, indent=2))

asyncio.run(main())
"
```

Expected SQL Audit State:
```sql
-- 1. Confirm PROMOTED count is 0
SELECT COUNT(*) FROM ml_model_versions WHERE lifecycle_status = 'PROMOTED';
-- Expected Result: 0

-- 2. Confirm REJECTED count is preserved
SELECT COUNT(*) FROM ml_model_versions WHERE lifecycle_status = 'REJECTED';
-- Expected Result: >= 4

-- 3. Confirm prediction snapshots count is 0
SELECT COUNT(*) FROM ml_prediction_snapshots;
-- Expected Result: 0
```

---

## 4. Summary of 18 Certification Test Scenarios

| Test Function Name | Certification Requirement | Expected Result | Verified |
| :--- | :--- | :--- | :--- |
| `test_ws_10_5_01_eligible_candidate_discovery` | Candidate Discovery | Discovers `TRAINED_CANDIDATE` + `PROMOTION_ELIGIBLE` | ✅ PASS |
| `test_ws_10_5_02_phase_73_eligibility_verification` | Phase 7.3 Eligibility | Revalidates Phase 7.3 evaluation metrics | ✅ PASS |
| `test_ws_10_5_03_artifact_sha_verification` | Artifact SHA Verification | Verifies SHA-256 before promotion | ✅ PASS |
| `test_ws_10_5_04_successful_isolated_promotion` | Isolated Model Promotion | Promotes candidate to `PROMOTED` status | ✅ PASS |
| `test_ws_10_5_05_rejected_candidate_protection` | Rejected Protection | Blocks promotion of `REJECTED` candidate | ✅ PASS |
| `test_ws_10_5_06_pending_evaluation_protection` | Pending Protection | Blocks promotion of `PENDING_EVALUATION` | ✅ PASS |
| `test_ws_10_5_07_artifact_mutation_protection` | Artifact Mutation Protection | Blocks promotion on `ARTIFACT_MUTATION_DETECTED` | ✅ PASS |
| `test_ws_10_5_08_missing_dataset_protection` | Missing Dataset Protection | Blocks promotion when dataset does not exist | ✅ PASS |
| `test_ws_10_5_09_lineage_validation` | Lineage Validation | Blocks promotion for non-`FeatureSetV1` | ✅ PASS |
| `test_ws_10_5_10_retirement_protection` | Retirement Protection | Blocks promotion of `RETIRED` candidate | ✅ PASS |
| `test_ws_10_5_11_duplicate_promotion_idempotency` | Idempotency | Handles duplicate promotion attempt safely | ✅ PASS |
| `test_ws_10_5_12_concurrent_promotion_protection` | Concurrent Race Protection | Allows exactly 1 promotion across workers | ✅ PASS |
| `test_ws_10_5_13_transaction_rollback` | Rollback Safety | Rollback on error preserves candidate state | ✅ PASS |
| `test_ws_10_5_14_audit_lineage` | Audit Lineage Persistence | Appends `MODEL_PROMOTED` event record | ✅ PASS |
| `test_ws_10_5_15_single_promoted_per_family_enforcement` | Single Model per Family | Enforces `uq_active_promoted_model_per_name` | ✅ PASS |
| `test_ws_10_5_16_real_registry_authority_integration` | Registry Authority | Integrates with `MLModelRegistryRepository` | ✅ PASS |
| `test_ws_10_5_17_zero_snapshot_creation_during_promotion` | Zero Snapshot Creation | Zero snapshots created during promotion | ✅ PASS |
| `test_ws_10_5_18_production_state_safety` | Production State Safety | Asserts real database safety | ✅ PASS |
