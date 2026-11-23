import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { PredictiveIntelligencePage } from '../pages/PredictiveIntelligencePage';
import { AppLayout } from '../../../layouts/AppLayout';

// Mocks
vi.mock('../../../store/auth', () => ({
  useAuthStore: () => ({ user: { username: 'Admin Operator' }, token: 'mock-token' }),
}));

vi.mock('../../../store/app', () => ({
  useAppStore: () => ({ isSidebarCollapsed: false, toggleSidebar: vi.fn() }),
}));

describe('WS-09 Phase 7.7 Predictive Operational Integration & Decision Intelligence Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockNotConfiguredAuthority = {
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
    },
  };

  const mockNotConfiguredOperational = {
    success: true,
    data: {
      overall_authority_status: 'NOT_CONFIGURED',
      promoted_model_count: 0,
      total_snapshots_found: 0,
      prioritization: {
        top_delayed_dispatches: [],
        high_sla_risk_dispatches: [],
        high_plant_risk_dispatches: [],
      },
      snapshots: [],
      calculation_status: 'NOT_CONFIGURED',
      calculation_notes: 'PREDICTION AUTHORITY = NOT_CONFIGURED.',
    },
  };

  const mockAuthoritativeOverview = {
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
          active_version: 'v1.0.0-PROMOTED',
          artifact_sha256: '5c138abc1234def',
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: '2026-08-17T12:00:00Z',
        },
      ],
    },
  };

  const mockAuthoritativeOperational = {
    success: true,
    data: {
      overall_authority_status: 'AUTHORITATIVE',
      promoted_model_count: 1,
      total_snapshots_found: 1,
      prioritization: {
        top_delayed_dispatches: [
          {
            id: 'uuid-1',
            prediction_snapshot_id: 'SNAP-2026-001',
            idempotency_key: 'IK-001',
            prediction_timestamp: '2026-08-17T12:00:00Z',
            prediction_status: 'AUTHORITATIVE',
            model_name: 'delay_regressor',
            model_version: 'v1.0.0-PROMOTED',
            artifact_sha256: '5c138abc1234def',
            feature_set_version: 'FeatureSetV1',
            dispatch_id: 'DISP-101',
            dispatch_code: 'DSP-2026-101',
            plant_code: 'P-001',
            plant_name: 'Plant P-001',
            customer_code: 'C-001',
            customer_name: 'Customer C-001',
            vehicle_code: 'V-001',
            target_name: 'predicted_delay_mins',
            predicted_value: 18.5,
            confidence_score: 0.94,
            input_features: { avg_prior_delay_mins: 12.0 },
            prediction_outputs: { delay_prediction: 18.5 },
            lineage_metadata: {},
          },
        ],
        high_sla_risk_dispatches: [],
        high_plant_risk_dispatches: [],
      },
      snapshots: [
        {
          id: 'uuid-1',
          prediction_snapshot_id: 'SNAP-2026-001',
          idempotency_key: 'IK-001',
          prediction_timestamp: '2026-08-17T12:00:00Z',
          prediction_status: 'AUTHORITATIVE',
          model_name: 'delay_regressor',
          model_version: 'v1.0.0-PROMOTED',
          artifact_sha256: '5c138abc1234def',
          feature_set_version: 'FeatureSetV1',
          dispatch_id: 'DISP-101',
          dispatch_code: 'DSP-2026-101',
          plant_code: 'P-001',
          plant_name: 'Plant P-001',
          customer_code: 'C-001',
          customer_name: 'Customer C-001',
          vehicle_code: 'V-001',
          target_name: 'predicted_delay_mins',
          predicted_value: 18.5,
          confidence_score: 0.94,
          input_features: { avg_prior_delay_mins: 12.0 },
          prediction_outputs: { delay_prediction: 18.5 },
          lineage_metadata: {},
        },
      ],
      calculation_status: 'SUCCESS',
      calculation_notes: 'Retrieved 1 authoritative prediction snapshots',
    },
  };

  it('1. NOT_CONFIGURED operational state renders safe warning and empty lists', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      if (urlStr.includes('predictive/operational-overview')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredOperational), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('prioritization-not-configured')).toBeDefined();
    });

    expect(screen.getByText('Operational Risk Prioritization Disabled')).toBeDefined();
  });

  it('2. AUTHORITATIVE prediction rendering surfaces operational prioritization and dispatches', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockAuthoritativeOverview), { status: 200 }));
      }
      if (urlStr.includes('predictive/operational-overview')) {
        return Promise.resolve(new Response(JSON.stringify(mockAuthoritativeOperational), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/predictive-intelligence" element={<PredictiveIntelligencePage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('snapshot-row-SNAP-2026-001')).toBeDefined();
    });

    expect(screen.getAllByText('DSP-2026-101').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('18.5 mins')).toBeDefined();
  });

  it('3. NO_DATA state explicitly distinguishes NO_DATA from NOT_CONFIGURED', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockAuthoritativeOverview), { status: 200 }));
      }
      if (urlStr.includes('predictive/operational-overview')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              success: true,
              data: { ...mockAuthoritativeOperational.data, snapshots: [], prioritization: { top_delayed_dispatches: [], high_sla_risk_dispatches: [], high_plant_risk_dispatches: [] } },
            }),
            { status: 200 }
          )
        );
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('snapshots-empty-state')).toBeDefined();
    });

    expect(screen.getByText('No Prediction Snapshots Found (NO_DATA)')).toBeDefined();
  });

  it('4. API error state displays clear operational error', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      if (urlStr.includes('predictive/operational-overview')) {
        return Promise.resolve(
          new Response(JSON.stringify({ success: false, message: 'Database query timeout' }), { status: 500 })
        );
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('snapshots-error')).toBeDefined();
    });

    expect(screen.getByText('Database query timeout')).toBeDefined();
  });

  it('5. Interactive snapshot drill-down modal opens and exposes complete lineage', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockAuthoritativeOverview), { status: 200 }));
      }
      if (urlStr.includes('predictive/operational-overview')) {
        return Promise.resolve(new Response(JSON.stringify(mockAuthoritativeOperational), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('drilldown-button-SNAP-2026-001')).toBeDefined();
    });

    fireEvent.click(screen.getByTestId('drilldown-button-SNAP-2026-001'));

    await waitFor(() => {
      expect(screen.getByTestId('snapshot-drilldown-modal')).toBeDefined();
    });

    expect(screen.getByText('Snapshot Lineage & Provenance: SNAP-2026-001')).toBeDefined();
    expect(screen.getByText('5c138abc1234def')).toBeDefined();

    fireEvent.click(screen.getByTestId('close-modal-button'));

    await waitFor(() => {
      expect(screen.queryByTestId('snapshot-drilldown-modal')).toBeNull();
    });
  });
});
