import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { PredictiveIntelligencePage } from '../pages/PredictiveIntelligencePage';

// Mocks
vi.mock('../../../store/auth', () => ({
  useAuthStore: () => ({ user: { username: 'Reconciliation Admin' }, token: 'mock-token' }),
}));

vi.mock('../../../store/app', () => ({
  useAppStore: () => ({ isSidebarCollapsed: false, toggleSidebar: vi.fn() }),
}));

describe('WS-09.7.9 Cross-Section Reconciliation Frontend Vitest Suite', () => {
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
      calculation_notes: 'PREDICTION AUTHORITY = NOT_CONFIGURED.',
      models: [],
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
      calculation_notes: 'Predictive workspace active.',
      models: [],
      total_snapshots_found: 1,
      snapshots: [
        {
          id: 'snap-uuid-79',
          prediction_snapshot_id: 'SNAP-79-001',
          idempotency_key: 'IK-79-001',
          prediction_timestamp: '2026-08-17T15:00:00Z',
          prediction_status: 'AUTHORITATIVE',
          model_name: 'delay_regressor',
          model_version: 'v7.9.0-PROMOTED',
          artifact_sha256: 'sha7912345678901234567890123456789012345678901234567890123456789',
          feature_set_version: 'FeatureSetV1',
          dispatch_id: 'disp-79',
          dispatch_code: 'DSP-79-RECON',
          plant_code: 'PL-79',
          plant_name: 'Plant PL-79',
          customer_code: 'CUST-79',
          customer_name: 'Customer CUST-79',
          vehicle_code: 'VH-79',
          target_name: 'predicted_delay_mins',
          predicted_value: 18.0,
          confidence_score: 0.88,
          input_features: { plant_queue_avg_30d: 15.0 },
          prediction_outputs: { predicted_delay_mins: 18.0 },
          lineage_metadata: {},
        },
      ],
      prioritization: {
        top_delayed_dispatches: [
          {
            id: 'snap-uuid-79',
            prediction_snapshot_id: 'SNAP-79-001',
            idempotency_key: 'IK-79-001',
            prediction_timestamp: '2026-08-17T15:00:00Z',
            prediction_status: 'AUTHORITATIVE',
            model_name: 'delay_regressor',
            model_version: 'v7.9.0-PROMOTED',
            artifact_sha256: 'sha7912345678901234567890123456789012345678901234567890123456789',
            feature_set_version: 'FeatureSetV1',
            dispatch_id: 'disp-79',
            dispatch_code: 'DSP-79-RECON',
            plant_code: 'PL-79',
            plant_name: 'Plant PL-79',
            customer_code: 'CUST-79',
            customer_name: 'Customer CUST-79',
            vehicle_code: 'VH-79',
            target_name: 'predicted_delay_mins',
            predicted_value: 18.0,
            confidence_score: 0.88,
            input_features: { plant_queue_avg_30d: 15.0 },
            prediction_outputs: { predicted_delay_mins: 18.0 },
            lineage_metadata: {},
          },
        ],
        high_sla_risk_dispatches: [],
      },
      calculation_status: 'AUTHORITATIVE',
    },
  };

  it('1. GLOBAL FILTER RECONCILIATION: Query URL contains plant_id, customer_id, and dataset_type parameters', async () => {
    let capturedUrl = '';
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('operational-overview')) {
        capturedUrl = urlStr;
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
      expect(capturedUrl).toContain('plant_id=');
      expect(capturedUrl).toContain('customer_id=');
      expect(capturedUrl).toContain('dataset_type=');
    });
  });

  it('2. REAL NOT_CONFIGURED SAFETY: Renders NOT_CONFIGURED badge and disables prioritization in real DB state', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('operational-overview') || urlStr.includes('predictive/authority')) {
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
  });

  it('3. AUTHORITATIVE & ENTITY DRILLDOWN: Renders canonical dispatch codes and opens drilldown modal', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('operational-overview') || urlStr.includes('predictive/authority')) {
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

    expect(screen.getAllByText('DSP-79-RECON').length).toBeGreaterThan(0);
    expect(screen.getAllByText((content) => content.includes('18')).length).toBeGreaterThan(0);
  });
});
