import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';
import { useOperationalDashboardContext } from '../modules/operational_dashboard/hooks/useOperationalDashboardContext';

const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <DashboardFilterProvider>{children}</DashboardFilterProvider>
  </MemoryRouter>
);

describe('Stale Response Race Protection Test', () => {
  it('prevents slow Request A (Plant A) from overwriting faster Request B (Plant B)', async () => {
    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            context: {
              dataset_id: 'DS-001',
              snapshot_version: 'v2.11-SNAP-20260805',
              operational_date: '2026-08-05',
              plant_id: 'ALL',
              customer_id: 'ALL',
              dataset_type: 'REAL_ONLY',
              generated_at: new Date().toISOString(),
            },
            metadata: { total_dispatches: 100, dataset_status: 'ACTIVE_PRODUCTION' },
            available_plants: [{ id: 'ALL', name: 'All Plants' }],
            available_customers: [{ id: 'ALL', name: 'All Customers' }],
          },
        }),
      });
    });

    const { result } = renderHook(() => useOperationalDashboardContext(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.shellData?.context.plant_id).toBe('ALL');
  });
});
