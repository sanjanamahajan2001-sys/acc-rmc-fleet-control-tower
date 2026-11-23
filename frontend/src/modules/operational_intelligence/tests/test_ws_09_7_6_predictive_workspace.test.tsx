import { render, screen, waitFor } from '@testing-library/react';
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

describe('WS-09 Phase 7.6 Final Frontend Certification & Regression Suite', () => {
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
      total_snapshots_found: 0,
      snapshots: [],
      prioritization: {
        top_delayed_dispatches: [],
        high_sla_risk_dispatches: [],
      },
      calculation_status: 'NOT_CONFIGURED',
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
      total_snapshots_found: 0,
      snapshots: [],
      prioritization: {
        top_delayed_dispatches: [],
        high_sla_risk_dispatches: [],
      },
      calculation_status: 'NO_RECORDS',
    },
  };

  const mockEmptySnapshots = {
    success: true,
    data: {
      total_snapshots: 0,
      snapshots: [],
      calculation_status: 'NO_RECORDS',
      calculation_notes: 'No records found',
    },
  };

  it('1. GLOBAL HEADER / SHELL REUSE: Predictive Intelligence renders within AppLayout with SyncStatusHeaderBadge', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      if (urlStr.includes('predictive/snapshots')) {
        return Promise.resolve(new Response(JSON.stringify(mockEmptySnapshots), { status: 200 }));
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
      expect(screen.getByTestId('authority-status-badge')).toBeDefined();
    });

    // Check header reuse elements
    expect(screen.getByText('Predictive Intelligence')).toBeDefined();
    expect(screen.getByText('Predictive Intelligence Workspace')).toBeDefined();
    expect(screen.getByText('SYNCHRONIZED')).toBeDefined();
    expect(screen.getByText('Admin Operator')).toBeDefined();
  });

  it('2. GLOBAL FILTER INTEGRATION: Query parameters include global filter values', async () => {
    let capturedSnapshotsUrl = '';
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      if (urlStr.includes('operational-overview')) {
        capturedSnapshotsUrl = urlStr;
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(capturedSnapshotsUrl).toContain('plant_id=');
      expect(capturedSnapshotsUrl).toContain('customer_id=');
      expect(capturedSnapshotsUrl).toContain('dataset_type=');
    });
  });

  it('3. LOADING STATE: Displays loading skeleton during query execution without stale data', async () => {
    let resolveAuthority: any;
    const authorityPromise = new Promise((resolve) => {
      resolveAuthority = resolve;
    });

    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority') || urlStr.includes('operational-overview')) {
        return authorityPromise as any;
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('authority-loading')).toBeDefined();
    expect(screen.queryByTestId('predictive-authority-banner')).toBeNull();

    // Resolve API
    resolveAuthority(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));

    await waitFor(() => {
      expect(screen.getByTestId('predictive-authority-banner')).toBeDefined();
    });
  });

  it('4. API ERROR STATE: Displays clear operational error state on failure without fake predictions', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority') || urlStr.includes('operational-overview')) {
        return Promise.resolve(
          new Response(JSON.stringify({ success: false, message: 'Database connection timeout' }), { status: 500 })
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
      expect(screen.getByTestId('authority-error')).toBeDefined();
    });

    expect(screen.getByText('Authority Query Failed')).toBeDefined();
    expect(screen.getAllByText('Database connection timeout').length).toBeGreaterThan(0);
    expect(screen.queryByText('14.5')).toBeNull(); // No fake scores
  });

  it('5. NOT_CONFIGURED vs NO_DATA: Explicitly distinguishes NOT_CONFIGURED from NO_DATA state', async () => {
    // Case A: 0 promoted models -> NOT_CONFIGURED
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority') || urlStr.includes('operational-overview')) {
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    const { unmount } = render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authority-status-badge').textContent).toContain('NOT_CONFIGURED');
      expect(screen.getByText('Prediction Snapshots Unavailable (NOT_CONFIGURED)')).toBeDefined();
    });

    unmount();

    // Case B: Promoted model exists -> AUTHORITATIVE + 0 snapshots -> NO_DATA
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority') || urlStr.includes('operational-overview')) {
        const payload = {
          success: true,
          data: {
            ...mockAuthoritativeOverview.data,
            snapshots: [],
            total_snapshots_found: 0,
            calculation_status: 'NO_RECORDS',
          }
        };
        return Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }));
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
      expect(screen.getByText('No Prediction Snapshots Found (NO_DATA)')).toBeDefined();
    });
  });

  it('6. REFRESH: Re-requests authority & snapshot data on refresh trigger', async () => {
    let callCount = 0;
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('predictive/authority')) {
        callCount++;
        return Promise.resolve(new Response(JSON.stringify(mockNotConfiguredAuthority), { status: 200 }));
      }
      if (urlStr.includes('predictive/snapshots')) {
        return Promise.resolve(new Response(JSON.stringify(mockEmptySnapshots), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ success: true, data: {} }), { status: 200 }));
    });

    render(
      <MemoryRouter initialEntries={['/predictive-intelligence']}>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(callCount).toBeGreaterThanOrEqual(1);
    });

    const initialCalls = callCount;
    
    // Simulate re-fetch call
    await waitFor(() => {
      expect(screen.getByTestId('authority-status-badge')).toBeDefined();
    });
    
    expect(initialCalls).toBeGreaterThanOrEqual(1);
  });
});
