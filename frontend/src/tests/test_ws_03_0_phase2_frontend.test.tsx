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

describe('WS-03.0 Phase 2 Frontend Context Hook Contract Tests', () => {
  it('1. Parses Phase 2 DTO response and updates context metadata', async () => {
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
              generated_at: '2026-08-12T07:00:00Z',
            },
            metadata: {
              total_dispatches: 3532,
              overall_total_dispatches: 3532,
              dataset_status: 'ACTIVE_PRODUCTION',
              sync_status: 'SYNCHRONIZED',
              e_tag: 'md5_hash_checksum_test',
            },
            available_plants: [{ id: 'ALL', name: 'All Plants' }],
            available_customers: [{ id: 'ALL', name: 'All Customers' }],
          },
        }),
      })
    );

    const { result } = renderHook(() => useOperationalDashboardContext(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.shellData?.context.dataset_id).toBe('DS-20260805-001');
    expect(result.current.shellData?.context.snapshot_version).toBe('v2.11-SNAP-20260805');
    expect(result.current.shellData?.metadata.total_dispatches).toBe(3532);
  });

  it('2. Handles ERP Reset Zero-State Response correctly', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            context: {
              dataset_id: 'DS-20260805-001',
              snapshot_version: 'v2.11-SNAP-EMPTY',
              operational_date: '2025-08-15',
              plant_id: 'ALL',
              customer_id: 'ALL',
              dataset_type: 'REAL_ONLY',
              generated_at: '2026-08-12T07:00:00Z',
            },
            metadata: {
              total_dispatches: 0,
              overall_total_dispatches: 0,
              dataset_status: 'ZERO_RECORDS_EMPTY',
              sync_status: 'SYNCHRONIZED',
              e_tag: 'empty_hash_checksum',
            },
            available_plants: [{ id: 'ALL', name: 'All Plants' }],
            available_customers: [{ id: 'ALL', name: 'All Customers' }],
          },
        }),
      })
    );

    const { result } = renderHook(() => useOperationalDashboardContext(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.shellData?.context.snapshot_version).toBe('v2.11-SNAP-EMPTY');
    expect(result.current.shellData?.metadata.total_dispatches).toBe(0);
    expect(result.current.shellData?.metadata.dataset_status).toBe('ZERO_RECORDS_EMPTY');
  });

  it('3. Handles API 404/422 Error Responses gracefully without crashing', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({
          success: false,
          message: "Plant identifier 'NONEXISTENT_PLANT' not found in canonical database.",
        }),
      })
    );

    const { result } = renderHook(() => useOperationalDashboardContext(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Plant identifier 'NONEXISTENT_PLANT' not found in canonical database.");
  });
});
