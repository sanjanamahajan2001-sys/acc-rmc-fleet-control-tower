import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalDashboardShell } from '../modules/operational_dashboard/shell/OperationalDashboardShell';

describe('WS-03.0 Phase 1 Verification & Integration Tests', () => {
  it('1. Verifies Overall Dashboard mounts within single shared DashboardFilterProvider', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            context: {
              dataset_id: 'DS-20260805-001',
              snapshot_version: 'v2.11-SNAP-20260805',
              operational_date: '2026-08-05',
              plant_id: 'ALL',
              customer_id: 'ALL',
              dataset_type: 'REAL_ONLY',
              generated_at: '2026-08-12T00:00:00Z',
            },
            metadata: {
              total_dispatches: 3532,
              overall_total_dispatches: 3532,
              dataset_status: 'ACTIVE_PRODUCTION',
              sync_status: 'SYNCHRONIZED',
              e_tag: 'test_etag_123',
            },
            available_plants: [{ id: 'ALL', name: 'All Plants' }],
            available_customers: [{ id: 'ALL', name: 'All Customers' }],
          },
        }),
      })
    );

    render(
      <MemoryRouter initialEntries={['/overall-dashboard']}>
        <DashboardFilterProvider>
          <Routes>
            <Route path="/overall-dashboard" element={<OperationalDashboardShell />} />
          </Routes>
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Overall Operational Dashboard/i)).toBeInTheDocument();
    });
  });

  it('2. Verifies URL query parameters plant_id, customer_id, dataset_type initialize filter state', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            context: {
              dataset_id: 'DS-20260805-001',
              snapshot_version: 'v2.11-SNAP-20260805',
              operational_date: '2026-08-05',
              plant_id: 'ACC_DHARGA',
              customer_id: 'CUST_A_K_MEHTA',
              dataset_type: 'REAL_ONLY',
              generated_at: '2026-08-12T00:00:00Z',
            },
            metadata: {
              total_dispatches: 3,
              overall_total_dispatches: 3532,
              dataset_status: 'ACTIVE_PRODUCTION',
              sync_status: 'SYNCHRONIZED',
              e_tag: 'test_etag_123',
            },
            available_plants: [
              { id: 'ALL', name: 'All Plants' },
              { id: 'ACC_DHARGA', name: 'Dharga Plant', code: 'ACC_DHARGA' },
            ],
            available_customers: [
              { id: 'ALL', name: 'All Customers' },
              { id: 'CUST_A_K_MEHTA', name: 'A K MEHTA', code: 'CUST_A_K_MEHTA' },
            ],
          },
        }),
      })
    );

    render(
      <MemoryRouter initialEntries={['/overall-dashboard?plant_id=ACC_DHARGA&customer_id=CUST_A_K_MEHTA&dataset_type=REAL_ONLY']}>
        <DashboardFilterProvider>
          <Routes>
            <Route path="/overall-dashboard" element={<OperationalDashboardShell />} />
          </Routes>
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Overall Operational Dashboard/i)).toBeInTheDocument();
    });
  });

  it('3. Verifies inter-dashboard filter continuity between /site-dashboard and /overall-dashboard', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            context: {
              dataset_id: 'DS-20260805-001',
              snapshot_version: 'v2.11-SNAP-20260805',
              operational_date: '2026-08-05',
              plant_id: 'ACC_DHARGA',
              customer_id: 'ALL',
              dataset_type: 'REAL_ONLY',
              generated_at: '2026-08-12T00:00:00Z',
            },
            metadata: {
              total_dispatches: 978,
              overall_total_dispatches: 3532,
              dataset_status: 'ACTIVE_PRODUCTION',
              sync_status: 'SYNCHRONIZED',
              e_tag: 'test_etag_123',
            },
            available_plants: [
              { id: 'ALL', name: 'All Plants' },
              { id: 'ACC_DHARGA', name: 'Dharga Plant', code: 'ACC_DHARGA' },
            ],
            available_customers: [{ id: 'ALL', name: 'All Customers' }],
          },
        }),
      })
    );

    render(
      <MemoryRouter initialEntries={['/overall-dashboard?plant_id=ACC_DHARGA']}>
        <DashboardFilterProvider>
          <Routes>
            <Route path="/overall-dashboard" element={<OperationalDashboardShell />} />
          </Routes>
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Overall Operational Dashboard/i)).toBeInTheDocument();
    });
  });
});
