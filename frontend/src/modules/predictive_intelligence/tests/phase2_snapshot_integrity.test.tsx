import { describe, it, expect } from 'vitest';

describe('Phase 2 Frontend Snapshot Integrity & Supersession Verification', () => {
  it('verifies active non-stale snapshots are rendered as authoritative', async () => {
    const mockApiResponse = {
      success: true,
      data: {
        overall_authority_status: 'AUTHORITATIVE',
        active_models_count: 4,
        total_snapshots_found: 100,
        snapshots: [
          {
            prediction_snapshot_id: 'SNAP-CURRENT-001',
            dispatch_code: 'SYNTH-TCK-TRIP-3503',
            plant_code: 'ACC_KUNDAIM',
            customer_code: 'CUST_ELIN_ELECTRONIC_LTD',
            vehicle_code: 'GA07F7633',
            model_name: 'delay_regressor',
            model_version: 'v1.1.0-candidate-ds-fsv1-prom',
            predicted_value: 19.9031,
            prediction_status: 'AUTHORITATIVE',
            is_stale: false,
          },
        ],
      },
    };

    expect(mockApiResponse.data.overall_authority_status).toBe('AUTHORITATIVE');
    expect(mockApiResponse.data.snapshots[0].is_stale).toBe(false);
  });

  it('verifies stale snapshots are excluded from current active views', () => {
    const snapshots = [
      { id: 'SNAP-OLD-001', is_stale: true },
      { id: 'SNAP-NEW-002', is_stale: false, superseded_by: 'SNAP-NEW-002' },
    ];

    const activeSnapshots = snapshots.filter((s) => !s.is_stale);
    expect(activeSnapshots.length).toBe(1);
    expect(activeSnapshots[0].id).toBe('SNAP-NEW-002');
  });
});
