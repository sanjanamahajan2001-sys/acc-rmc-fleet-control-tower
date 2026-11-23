import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { PredictiveIntelligencePage } from '../pages/PredictiveIntelligencePage';

// Mocks
vi.mock('../../../store/auth', () => ({
  useAuthStore: () => ({ user: { username: 'Admin Operator' }, token: 'mock-token' }),
}));

vi.mock('../../../store/app', () => ({
  useAppStore: () => ({ isSidebarCollapsed: false, toggleSidebar: vi.fn() }),
}));

describe('WS-09 Phase 7.8 Master E2E Integration Vitest Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockNotConfiguredResponse = {
    success: true,
    data: {
      overall_authority_status: 'NOT_CONFIGURED',
      total_model_families: 4,
      promoted_model_count: 0,
      rejected_model_count: 4,
      calculation_notes: 'PREDICTION AUTHORITY = NOT_CONFIGURED. All 4 candidate models are REJECTED.',
      models: [
        {
          model_name: 'delay_regressor',
          target_name: 'predicted_delay_mins',
          model_category: 'Regression',
          prediction_authority: 'NOT_CONFIGURED',
          active_version: null,
          artifact_sha256: null,
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: null,
        },
      ],
      total_snapshots_found: 0,
      snapshots: [],
      prioritization: {
        top_delayed_dispatches: [],
        high_sla_risk_dispatches: [],
      },
      calculation_status: 'NOT_CONFIGURED',
    },
  };

  const mockAuthoritativeResponse = {
    success: true,
    data: {
      overall_authority_status: 'AUTHORITATIVE',
      total_model_families: 4,
      promoted_model_count: 1,
      rejected_model_count: 3,
      calculation_notes: 'Predictive workspace configured with 1/4 active promoted models.',
      models: [
        {
          model_name: 'delay_regressor',
          target_name: 'predicted_delay_mins',
          model_category: 'Regression',
          prediction_authority: 'AUTHORITATIVE',
          active_version: 'v7.8.0-PROMOTED',
          artifact_sha256: '5c138abc1234def5678901234567890123456789012345678901234567890123',
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: '2026-08-17T12:00:00Z',
        },
      ],
      total_snapshots_found: 1,
      snapshots: [
        {
          id: 'snap-uuid-78',
          prediction_snapshot_id: 'SNAP-78-001',
          idempotency_key: 'IK-78-001',
          prediction_timestamp: '2026-08-17T14:00:00Z',
          prediction_status: 'AUTHORITATIVE',
          model_name: 'delay_regressor',
          model_version: 'v7.8.0-PROMOTED',
          artifact_sha256: '5c138abc1234def5678901234567890123456789012345678901234567890123',
          feature_set_version: 'FeatureSetV1',
          dispatch_id: 'disp-78',
          dispatch_code: 'DSP-78-E2E',
          plant_code: 'PL-78',
          plant_name: 'Plant PL-78',
          customer_code: 'CUST-78',
          customer_name: 'Customer CUST-78',
          vehicle_code: 'VH-78',
          target_name: 'predicted_delay_mins',
          predicted_value: 24.5,
          confidence_score: 0.92,
          input_features: { avg_prior_delay_mins: 15.0 },
          prediction_outputs: { predicted_delay_mins: 24.5 },
          lineage_metadata: {},
        },
      ],
      prioritization: {
        top_delayed_dispatches: [
          {
            id: 'snap-uuid-78',
            prediction_snapshot_id: 'SNAP-78-001',
            idempotency_key: 'IK-78-001',
            prediction_timestamp: '2026-08-17T14:00:00Z',
            prediction_status: 'AUTHORITATIVE',
            model_name: 'delay_regressor',
            model_version: 'v7.8.0-PROMOTED',
            artifact_sha256: '5c138abc1234def5678901234567890123456789012345678901234567890123',
            feature_set_version: 'FeatureSetV1',
            dispatch_id: 'disp-78',
            dispatch_code: 'DSP-78-E2E',
            plant_code: 'PL-78',
            plant_name: 'Plant PL-78',
            customer_code: 'CUST-78',
            customer_name: 'Customer CUST-78',
            vehicle_code: 'VH-78',
            target_name: 'predicted_delay_mins',
            predicted_value: 24.5,
            confidence_score: 0.92,
            input_features: { avg_prior_delay_mins: 15.0 },
            prediction_outputs: { predicted_delay_mins: 24.5 },
            lineage_metadata: {},
          },
        ],
        high_sla_risk_dispatches: [],
        high_plant_risk_dispatches: [],
      },
      calculation_status: 'AUTHORITATIVE',
    },
  };

  it('1. REAL NOT_CONFIGURED SAFETY: Renders warning banner and disables prioritization', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority') || urlStr.includes('operational-overview')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredResponse), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authority-status-badge').textContent).toContain('NOT_CONFIGURED');
    });

    expect(screen.getByText('Operational Risk Prioritization Disabled')).toBeDefined();
    expect(screen.getByText('Prediction Snapshots Unavailable (NOT_CONFIGURED)')).toBeDefined();
  });

  it('2. AUTHORITATIVE & LINEAGE DRILL-DOWN: Renders prioritization cards and opens lineage modal', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority') || urlStr.includes('operational-overview')) {
        return Promise.resolve(new Response(JSON.stringify(mockAuthoritativeResponse), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authority-status-badge').textContent).toContain('AUTHORITATIVE');
    });

    expect(screen.getAllByText('DSP-78-E2E').length).toBeGreaterThan(0);
    expect(screen.getByText('24.5 mins')).toBeDefined();

    // Click Lineage button
    const drilldownBtn = screen.getByTestId('drilldown-button-SNAP-78-001');
    drilldownBtn.click();

    await waitFor(() => {
      expect(screen.getByTestId('snapshot-drilldown-modal')).toBeDefined();
    });

    expect(screen.getByText('Snapshot Lineage & Provenance: SNAP-78-001')).toBeDefined();
  });
});
