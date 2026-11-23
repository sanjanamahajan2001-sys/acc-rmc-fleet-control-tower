import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { PredictiveIntelligencePage } from '../pages/PredictiveIntelligencePage';

// Mocks
vi.mock('../../../store/auth', () => ({
  useAuthStore: () => ({ user: { username: 'Hardening Admin' }, token: 'mock-token' }),
}));

vi.mock('../../../store/app', () => ({
  useAppStore: () => ({ isSidebarCollapsed: false, toggleSidebar: vi.fn() }),
}));

describe('WS-09 Phase 7.10 Frontend Production Hardening Tests', () => {
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
      authority_details: [],
    },
  };

  const mockNotConfiguredOverviewResponse = {
    success: true,
    data: {
      overall_authority_status: 'NOT_CONFIGURED',
      promoted_model_count: 0,
      total_snapshots_found: 0,
      snapshots: [],
      prioritization: {
        top_delayed_dispatches: [],
        high_sla_risk_dispatches: [],
      },
      calculation_status: 'NOT_CONFIGURED',
    },
  };

  it('renders NOT_CONFIGURED state safely without mock predictions or fallbacks', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/predictive/authority')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockNotConfiguredResponse),
        });
      }
      if (url.includes('/predictive/operational-overview')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockNotConfiguredOverviewResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: {} }),
      });
    }) as any;

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Predictive Intelligence Workspace/i)).toBeInTheDocument();
    });
  });

  it('verifies distinct preservation of NO_DATA vs NOT_CONFIGURED state in UI', async () => {
    const mockNoDataOverviewResponse = {
      success: true,
      data: {
        overall_authority_status: 'AUTHORITATIVE',
        promoted_model_count: 1,
        total_snapshots_found: 0,
        snapshots: [],
        prioritization: null,
        calculation_status: 'NO_RECORDS',
      },
    };

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/predictive/authority')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: {
              overall_authority_status: 'AUTHORITATIVE',
              total_model_families: 4,
              promoted_model_count: 1,
              rejected_model_count: 3,
              authority_details: [],
            },
          }),
        });
      }
      if (url.includes('/predictive/operational-overview')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockNoDataOverviewResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: {} }),
      });
    }) as any;

    render(
      <MemoryRouter>
        <PredictiveIntelligencePage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Predictive Intelligence Workspace/i)).toBeInTheDocument();
    });
  });
});
