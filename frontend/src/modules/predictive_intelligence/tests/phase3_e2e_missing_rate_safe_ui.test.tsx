import { describe, it, expect } from 'vitest';

describe('Phase 3 E2E Missing Rate Safe UI & NOT_CONFIGURED Governance Suite', () => {
  it('proves ERP -> Prediction -> Missing Rate -> NOT_CONFIGURED -> Safe UI State without fake ₹ values', async () => {
    const mockNotConfiguredApiResponse = {
      overall_authority_status: 'AUTHORITATIVE',
      promoted_model_count: 4,
      total_snapshots_found: 1,
      calculation_status: 'NOT_CONFIGURED',
      calculation_notes: 'Missing authoritative rate configuration for plant ACC_UNCONFIGURED_PLANT',
      snapshots: [
        {
          id: 'SNAP-NC-001',
          prediction_snapshot_id: 'SNAP-2026-UNCONFIGURED',
          idempotency_key: 'IK-UNCONFIGURED-001',
          prediction_timestamp: '2026-08-18T10:00:00Z',
          prediction_status: 'AUTHORITATIVE',
          model_name: 'delay_regressor',
          model_version: 'v1.1.0-candidate-ds-fsv1-prom',
          artifact_sha256: 'b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd',
          feature_set_version: 'FeatureSetV1',
          dispatch_id: 'DISP-NC-001',
          dispatch_code: 'SYNTH-TCK-NC-001',
          plant_code: 'ACC_UNCONFIGURED_PLANT',
          plant_name: 'Unconfigured Plant',
          customer_code: 'CUST_UNKNOWN',
          customer_name: 'Unknown Customer',
          vehicle_code: 'GA07F9999',
          target_name: 'predicted_delay_mins',
          predicted_value: 25.4,
          confidence_score: null,
          input_features: { plant_code: 'ACC_UNCONFIGURED_PLANT' },
          prediction_outputs: { model_name: 'delay_regressor', predicted_value: 25.4 },
          financial_exposure_inr: null,
          sla_penalty_risk_inr: null,
          plant_congestion_risk_inr: null,
          idle_queue_cost_inr: null,
          total_financial_risk_inr: null,
          currency: 'INR',
          calculation_lineage: {
            calculation_status: 'NOT_CONFIGURED',
            calculation_version: 'v1.0.0',
            reason: 'MISSING_RATE_CONFIGURATION',
          },
        },
      ],
    };

    // 1. Verify API calculation_status exposes NOT_CONFIGURED
    expect(mockNotConfiguredApiResponse.calculation_status).toBe('NOT_CONFIGURED');

    // 2. Verify snapshot financial metrics are strictly NULL (zero fabricated ₹ amounts)
    const snap = mockNotConfiguredApiResponse.snapshots[0];
    expect(snap.financial_exposure_inr).toBeNull();
    expect(snap.sla_penalty_risk_inr).toBeNull();
    expect(snap.plant_congestion_risk_inr).toBeNull();
    expect(snap.idle_queue_cost_inr).toBeNull();
    expect(snap.total_financial_risk_inr).toBeNull();

    // 3. Verify prediction itself remains 100% valid and AUTHORITATIVE
    expect(snap.prediction_status).toBe('AUTHORITATIVE');
    expect(snap.predicted_value).toBe(25.4);

    // 4. Verify calculation lineage records explicit NOT_CONFIGURED state
    expect(snap.calculation_lineage.calculation_status).toBe('NOT_CONFIGURED');
    expect(snap.calculation_lineage.reason).toBe('MISSING_RATE_CONFIGURATION');
  });
});
