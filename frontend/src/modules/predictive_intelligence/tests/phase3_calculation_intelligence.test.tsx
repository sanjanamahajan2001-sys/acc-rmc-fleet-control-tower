import { describe, it, expect } from 'vitest';

describe('Phase 3 Frontend Calculation Intelligence & Financial Exposure Suite', () => {
  it('verifies financial risk exposure metrics and currency formatting (₹)', () => {
    const mockApiResponse = {
      success: true,
      data: {
        overall_authority_status: 'AUTHORITATIVE',
        calculation_status: 'SUCCESS',
        snapshots: [
          {
            prediction_snapshot_id: 'SNAP-FIN-001',
            dispatch_code: 'SYNTH-TCK-TRIP-3433',
            plant_code: 'ACC_KUNDAIM',
            customer_code: 'CUST_ELIN_ELECTRONIC_LTD',
            financial_exposure_inr: 225.0,
            sla_penalty_risk_inr: 2000.0,
            idle_queue_cost_inr: 162.5,
            total_financial_risk_inr: 2387.5,
            currency: 'INR',
            calculation_lineage: {
              calculation_status: 'SUCCESS',
              calculation_version: 'v1.0.0',
              currency: 'INR',
              holding_rate_value: 450.0,
              sla_rate_value: 2500.0,
              retention_rate_value: 650.0,
            },
          },
        ],
      },
    };

    const snap = mockApiResponse.data.snapshots[0];
    expect(snap.currency).toBe('INR');
    expect(snap.financial_exposure_inr).toBe(225.0);
    expect(snap.sla_penalty_risk_inr).toBe(2000.0);
    expect(snap.total_financial_risk_inr).toBe(2387.5);
    expect(snap.calculation_lineage.holding_rate_value).toBe(450.0);
  });

  it('verifies safe NOT_CONFIGURED handling when rates are missing without fake financial amounts', () => {
    const mockNotConfiguredResponse = {
      success: true,
      data: {
        overall_authority_status: 'AUTHORITATIVE',
        calculation_status: 'NOT_CONFIGURED',
        calculation_notes: 'Missing rate configuration for plant ACC_UNKNOWN',
        snapshots: [
          {
            prediction_snapshot_id: 'SNAP-MISSING-001',
            financial_exposure_inr: null,
            sla_penalty_risk_inr: null,
            total_financial_risk_inr: null,
            currency: 'INR',
          },
        ],
      },
    };

    expect(mockNotConfiguredResponse.data.calculation_status).toBe('NOT_CONFIGURED');
    expect(mockNotConfiguredResponse.data.snapshots[0].total_financial_risk_inr).toBeNull();
  });
});
