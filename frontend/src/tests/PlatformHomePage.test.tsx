import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PlatformHomePage } from '../modules/home/pages/PlatformHomePage';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

// Mock Auth Store
vi.mock('../store/auth', () => ({
  useAuthStore: () => ({
    user: { role: 'ADMIN', username: 'Admin Operator' },
    clearAuth: vi.fn(),
  }),
}));

describe('PlatformHomePage Execution & Data-Binding Verification', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Mock API Endpoint Returns
    global.fetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              plants: [],
              customers: [],
              dataset_info: {
                operational_date: '2025-08-15',
                dataset_id: 'DS-20260805-001',
                import_timestamp: '2026-08-21T12:00:00Z',
                dataset_status: 'ACTIVE_PRODUCTION',
                total_dispatches: 3532,
              },
            },
          }),
        });
      }

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/operational-dashboard/kpis`)) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              kpis: {
                total_dispatches: { current_value: 3532 },
                dispatch_accuracy: { current_value: 63.2 },
              },
            },
          }),
        });
      }

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/site-performance/aggregates`)) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              holding_breaches: 1300,
            },
          }),
        });
      }

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts/summary`)) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              active_critical_count: 1300,
            },
          }),
        });
      }

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/actions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            pending_count: 5,
            items: [
              {
                action_id: 'ACT-001',
                action_type: 'RE_ROUTE_VEHICLE',
                plant_code: 'ACC VASCO',
                action_status: 'PENDING',
              },
            ],
          }),
        });
      }

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            items: [
              {
                id: 'ALT-001',
                message: 'Overdue Unloading @ Dharga Site',
                severity: 'CRITICAL',
              },
            ],
          }),
        });
      }

      if (urlStr.includes(`${env.VITE_API_BASE_URL}/predictive/telemetry')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              active_authority_version: 'v2.11-LIVE',
              total_valid_snapshots: 12000,
              batch_watermark_state: 'OPTIMAL',
            },
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      });
    });
  });

  it('1. Zone 1 Command Header & Dataset Context Renders Correctly', async () => {
    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <PlatformHomePage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Platform Command Center')).toBeInTheDocument();
      expect(screen.getByText('2025-08-15')).toBeInTheDocument();
      expect(screen.getByText('SYNCHRONIZED')).toBeInTheDocument();
    });
  });

  it('2. Zone 2 Executive KPI Ribbon Binds Authoritative DTO Fields (Zero React Aggregation)', async () => {
    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <PlatformHomePage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('TOTAL DISPATCHES')).toBeInTheDocument();
      expect(screen.getAllByText('3,532').length).toBeGreaterThan(0);
      expect(screen.getByText('DISPATCH ACCURACY')).toBeInTheDocument();
      expect(screen.getByText('63.2%')).toBeInTheDocument();
      expect(screen.getByText('HOLDING BREACHES')).toBeInTheDocument();
      expect(screen.getAllByText('1,300').length).toBeGreaterThan(0);
      expect(screen.getByText('CRITICAL ALERTS')).toBeInTheDocument();
      expect(screen.getByText('PENDING ACTIONS')).toBeInTheDocument();
    });
  });

  it('3. Zone 3 Needs Attention & Zone 4 Operational Pulse Render Live Data', async () => {
    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <PlatformHomePage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Needs Attention')).toBeInTheDocument();
      expect(screen.getByText('Overdue Unloading @ Dharga Site')).toBeInTheDocument();
      expect(screen.getByText('Predictive Intelligence Health')).toBeInTheDocument();
      expect(screen.getByText('v2.11-LIVE')).toBeInTheDocument();
    });
  });
});
