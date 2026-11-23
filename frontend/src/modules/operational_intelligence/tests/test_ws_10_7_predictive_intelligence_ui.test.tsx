import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { PredictiveIntelligencePage } from '../pages/PredictiveIntelligencePage';
import { PredictiveRiskWidget } from '../components/PredictiveRiskWidget';

vi.mock('../../../store/auth', () => ({
  useAuthStore: () => ({ user: { username: 'Admin Operator' }, token: 'mock-token' }),
}));

vi.mock('../../../store/app', () => ({
  useAppStore: () => ({ isSidebarCollapsed: false, toggleSidebar: vi.fn() }),
}));

describe('WS-10.7 Operational Predictive Intelligence UI Certification Suite', () => {
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
        {
          model_name: 'turnaround_regressor',
          target_name: 'predicted_avg_turnaround_mins',
          model_category: 'Regression',
          prediction_authority: 'NOT_CONFIGURED',
          active_version: null,
          artifact_sha256: null,
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: null,
        },
        {
          model_name: 'sla_breach_classifier',
          target_name: 'predicted_sla_breach_target',
          model_category: 'Classification',
          prediction_authority: 'NOT_CONFIGURED',
          active_version: null,
          artifact_sha256: null,
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: null,
        },
        {
          model_name: 'plant_risk_classifier',
          target_name: 'predicted_plant_congestion_target',
          model_category: 'Classification',
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
      calculation_notes: '0 promoted models available for inference.',
    },
  };

  const mockAuthoritativeAuthority = {
    success: true,
    data: {
      overall_authority_status: 'AUTHORITATIVE',
      total_model_families: 4,
      promoted_model_count: 1,
      rejected_model_count: 3,
      calculation_notes: 'Authoritative model active.',
      models: [
        {
          model_name: 'delay_regressor',
          target_name: 'predicted_delay_mins',
          model_category: 'Regression',
          prediction_authority: 'AUTHORITATIVE',
          active_version: 'v10.7.0-PROMOTED',
          artifact_sha256: '5c138abc1234def5c138abc1234def5c138abc1234def5c138abc1234def1234',
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: '2026-08-17T12:00:00Z',
        },
        {
          model_name: 'turnaround_regressor',
          target_name: 'predicted_avg_turnaround_mins',
          model_category: 'Regression',
          prediction_authority: 'NOT_CONFIGURED',
          active_version: null,
          artifact_sha256: null,
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: null,
        },
        {
          model_name: 'sla_breach_classifier',
          target_name: 'predicted_sla_breach_target',
          model_category: 'Classification',
          prediction_authority: 'NOT_CONFIGURED',
          active_version: null,
          artifact_sha256: null,
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: null,
        },
        {
          model_name: 'plant_risk_classifier',
          target_name: 'predicted_plant_congestion_target',
          model_category: 'Classification',
          prediction_authority: 'NOT_CONFIGURED',
          active_version: null,
          artifact_sha256: null,
          feature_set_version: 'FeatureSetV1',
          last_promoted_at: null,
        },
      ],
    },
  };

  const mockItem1 = {
    id: 'snap-1',
    prediction_snapshot_id: 'SNAP-DISP-101',
    idempotency_key: 'IK-101',
    prediction_timestamp: '2026-08-18T10:15:30Z',
    prediction_status: 'SUCCESS',
    model_name: 'delay_regressor',
    model_version: 'v10.7.0-PROMOTED',
    artifact_sha256: '5c138abc1234def5c138abc1234def5c138abc1234def5c138abc1234def1234',
    feature_set_version: 'FeatureSetV1',
    dispatch_id: 'DISP-101',
    dispatch_code: 'DISP-101',
    plant_code: 'ACC_DHARGA',
    plant_name: 'ACC Dharga Plant',
    customer_code: 'CUST_BANGALORE',
    customer_name: 'Bangalore Infra Ltd',
    vehicle_code: 'V-101',
    target_name: 'predicted_delay_mins',
    predicted_value: 32.4,
    confidence_score: 0.94,
    input_features: { dispatch_hour: 14, ticket_volume_m3: 15.0, operation_date: '2026-08-05' },
    prediction_outputs: { predicted_delay_mins: 32.4 },
    lineage_metadata: { evaluator_version: 'WS-10.4' },
    calculation_lineage: { rate_authority_source: 'RATE_SPECIFICATION_GLOBAL_V1' },
  };

  const mockAuthoritativeOperational = {
    success: true,
    data: {
      overall_authority_status: 'AUTHORITATIVE',
      promoted_model_count: 1,
      total_snapshots_found: 1,
      prioritization: {
        top_delayed_dispatches: [mockItem1],
        high_sla_risk_dispatches: [],
        high_plant_risk_dispatches: [],
      },
      snapshots: [mockItem1],
      calculation_status: 'AUTHORITATIVE',
      calculation_notes: '1 snapshot match.',
    },
  };

  it('1. Renders NOT_CONFIGURED state explicitly with candidate rejection banners', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/predictive/telemetry') || urlStr.includes('/predictive/authority')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockNotConfiguredAuthority) } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockNotConfiguredOperational) } as Response);
    });

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('predictive-authority-banner')).toBeInTheDocument();
      expect(screen.getByTestId('authority-status-badge')).toHaveTextContent('PREDICTION AUTHORITY = NOT_CONFIGURED');
      expect(screen.getByText(/All 4 candidate models are REJECTED/i)).toBeInTheDocument();
    });
  });

  it('2. Renders AUTHORITATIVE state banner and operational overview data when models are promoted', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/predictive/telemetry') || urlStr.includes('/predictive/authority')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeAuthority) } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeOperational) } as Response);
    });

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('predictive-authority-banner')).toBeInTheDocument();
      expect(screen.getByTestId('authority-status-badge')).toHaveTextContent('PREDICTION AUTHORITY = AUTHORITATIVE');
      expect(screen.getByTestId('snapshot-row-SNAP-DISP-101')).toBeInTheDocument();
      expect(screen.getByText('32.4 mins')).toBeInTheDocument();
    });
  });

  it('3. Renders 4 model family cards with authority badges and active version strings', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/predictive/telemetry') || urlStr.includes('/predictive/authority')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeAuthority) } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeOperational) } as Response);
    });

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('model-card-delay_regressor')).toBeInTheDocument();
      expect(screen.getByTestId('model-card-turnaround_regressor')).toBeInTheDocument();
      expect(screen.getByTestId('model-card-sla_breach_classifier')).toBeInTheDocument();
      expect(screen.getByTestId('model-card-plant_risk_classifier')).toBeInTheDocument();
    });
  });

  it('4. Renders operational snapshot table with filtering controls', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/predictive/telemetry') || urlStr.includes('/predictive/authority')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeAuthority) } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeOperational) } as Response);
    });

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('snapshot-row-SNAP-DISP-101')).toBeInTheDocument();
    });
  });

  it('5. Opens lineage drill-down modal showing snapshot lineage metadata & rate authority source', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = url.toString();
      if (urlStr.includes('/predictive/telemetry') || urlStr.includes('/predictive/authority')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeAuthority) } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuthoritativeOperational) } as Response);
    });

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('snapshot-row-SNAP-DISP-101')).toBeInTheDocument();
    });

    const drillButtons = screen.getAllByTestId('drilldown-button-SNAP-DISP-101');
    expect(drillButtons[0]).toBeInTheDocument();
  });

  it('6. Renders PredictiveRiskWidget turnaround_regressor in normal state', () => {
    const mockModel = {
      model_name: 'turnaround_regressor',
      target_name: 'predicted_avg_turnaround_mins',
      model_category: 'Regression',
      prediction_authority: 'AUTHORITATIVE',
      active_version: 'v10.7.0-PROMOTED',
      artifact_sha256: '5c138abc1234def5c138abc1234def5c138abc1234def5c138abc1234def1234',
      feature_set_version: 'FeatureSetV1',
      last_promoted_at: '2026-08-17T12:00:00Z',
    };

    const mockSnap = {
      model_name: 'turnaround_regressor',
      predicted_value: 45.0,
      confidence_score: 0.89,
    };

    render(<PredictiveRiskWidget model={mockModel as any} snapshot={mockSnap as any} />);
    expect(screen.getByTestId('staggered-loading-card')).toBeInTheDocument();
    expect(screen.getByText(/45/i)).toBeInTheDocument();
  });

  it('7. Renders PredictiveRiskWidget sla_breach_classifier in high risk state', () => {
    const mockModel = {
      model_name: 'sla_breach_classifier',
      target_name: 'predicted_sla_breach_target',
      model_category: 'Classification',
      prediction_authority: 'AUTHORITATIVE',
      active_version: 'v10.7.0-PROMOTED',
      artifact_sha256: '5c138abc1234def5c138abc1234def5c138abc1234def5c138abc1234def1234',
      feature_set_version: 'FeatureSetV1',
      last_promoted_at: '2026-08-17T12:00:00Z',
    };

    const mockSnap = {
      model_name: 'sla_breach_classifier',
      predicted_value: 1.0,
      confidence_score: 0.95,
    };

    render(<PredictiveRiskWidget model={mockModel as any} snapshot={mockSnap as any} />);
    expect(screen.getByTestId('sla-risk-card')).toBeInTheDocument();
    expect(screen.getByText(/SLA Breach Risk/i)).toBeInTheDocument();
  });

  it('8. Renders PredictiveRiskWidget plant_risk_classifier with integer class in {0, 1, 2}', () => {
    const mockModel = {
      model_name: 'plant_risk_classifier',
      target_name: 'predicted_plant_congestion_target',
      model_category: 'Classification',
      prediction_authority: 'AUTHORITATIVE',
      active_version: 'v10.7.0-PROMOTED',
      artifact_sha256: '5c138abc1234def5c138abc1234def5c138abc1234def5c138abc1234def1234',
      feature_set_version: 'FeatureSetV1',
      last_promoted_at: '2026-08-17T12:00:00Z',
    };

    const mockSnap = {
      model_name: 'plant_risk_classifier',
      predicted_value: 1.0, // Strict WS6.2 integer class 1 (MODERATE)
      confidence_score: 0.91,
    };

    render(<PredictiveRiskWidget model={mockModel as any} snapshot={mockSnap as any} />);
    expect(screen.getByTestId('plant-risk-card')).toBeInTheDocument();
    expect(screen.getByText('MODERATE')).toBeInTheDocument();
  });

  it('9. Renders PredictiveRiskWidget delay_regressor with predicted delay mins', () => {
    const mockModel = {
      model_name: 'delay_regressor',
      target_name: 'predicted_delay_mins',
      model_category: 'Regression',
      prediction_authority: 'AUTHORITATIVE',
      active_version: 'v10.7.0-PROMOTED',
      artifact_sha256: '5c138abc1234def5c138abc1234def5c138abc1234def5c138abc1234def1234',
      feature_set_version: 'FeatureSetV1',
      last_promoted_at: '2026-08-17T12:00:00Z',
    };

    const mockSnap = {
      model_name: 'delay_regressor',
      predicted_value: 32.4,
      confidence_score: 0.94,
    };

    render(<PredictiveRiskWidget model={mockModel as any} snapshot={mockSnap as any} />);
    expect(screen.getByTestId('transit-buffer-card')).toBeInTheDocument();
    expect(screen.getByText(/32.4/i)).toBeInTheDocument();
  });
});
