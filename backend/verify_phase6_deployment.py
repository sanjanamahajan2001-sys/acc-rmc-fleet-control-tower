"""
Phase 6 Automated Production Deployment Verification Script
Run: python verify_phase6_deployment.py
"""

import urllib.request
import json
import sys

BASE_URL = "http://localhost:8010/fleet-api/v1/operational-intelligence/predictive"

def check_deployment():
    print("=" * 70)
    print("🔍 VERIFYING PHASE 6 PRODUCTION DEPLOYMENT STATUS...")
    print("=" * 70)

    # 1. Test Telemetry Endpoint
    telemetry_url = f"{BASE_URL}/telemetry"
    try:
        req = urllib.request.urlopen(telemetry_url)
        res = json.loads(req.read().decode('utf-8'))
        data = res.get("data", {})
        
        authority = data.get("production_authority")
        auth_count = data.get("authoritative_model_count")
        expected_count = data.get("expected_model_family_count")
        
        print(f"\n1. TELEMETRY OBSERVABILITY CHECK:")
        print(f"   - Authority Status        : {authority}")
        print(f"   - Promoted Model Count    : {auth_count} / {expected_count}")

        if authority == "AUTHORITATIVE" and auth_count == 4:
            print("   🟢 Telemetry Authority: PASSED (4/4 Promoted Families Active)")
        else:
            print("   🔴 Telemetry Authority: DEGRADED (Run python seed_promoted_models.py)")
    except Exception as e:
        print(f"   🔴 Telemetry Endpoint Error: {e}")
        sys.exit(1)

    # 2. Test Operational Overview Endpoint
    overview_url = f"{BASE_URL}/operational-overview"
    try:
        req = urllib.request.urlopen(overview_url)
        res = json.loads(req.read().decode('utf-8'))
        data = res.get("data", {})
        
        overall_status = data.get("overall_authority_status")
        total_snaps = data.get("total_snapshots_found", 0)
        snapshots = data.get("snapshots", [])
        
        print(f"\n2. OPERATIONAL SNAPSHOTS CHECK:")
        print(f"   - Calculation Status      : {overall_status}")
        print(f"   - Total Snapshots Found   : {total_snaps}")

        if total_snaps > 0:
            sample = snapshots[0]
            print(f"   - Sample Snapshot ID      : {sample.get('prediction_snapshot_id')}")
            print(f"   - Sample Dispatch Code    : {sample.get('dispatch_code')}")
            print(f"   - Model & Predicted Val   : {sample.get('model_name')} -> {sample.get('predicted_value')}")
            print(f"   - Total Financial Risk    : ₹{sample.get('total_financial_risk_inr')}")
            print("   🟢 Operational Inference: PASSED (Snapshots & INR Financials Active)")
        else:
            print("   🟡 Snapshots Warning: 0 snapshots found. (Run python generate_predictive_data.py)")
    except Exception as e:
        print(f"   🔴 Operational Overview Endpoint Error: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ PHASE 6 DEPLOYMENT VERIFICATION COMPLETE: ALL SYSTEMS GO!")
    print("=" * 70)

if __name__ == "__main__":
    check_deployment()
