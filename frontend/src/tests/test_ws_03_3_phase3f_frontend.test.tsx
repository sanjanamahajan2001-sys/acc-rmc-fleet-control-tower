import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { useHoldingRetention } from '../modules/operational_dashboard/hooks/useHoldingRetention';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <DashboardFilterProvider>{children}</DashboardFilterProvider>
  </MemoryRouter>
);

describe('WS-03.3 Phase 3F — useHoldingRetention Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches holding & retention data and binds DTO metrics without calculation', async () => {
    const mockResponse = {
      success: true,
      data: {
        success: true,
        status: 'AVAILABLE',
        summary: {
          total_dispatches: 3532,
          total_holding_penalty_mins: 42142.0,
          total_retention_penalty_mins: 14490.0,
          total_lost_hours: 943.9,
        },
        data: [
          {
            hour_label: '00:00',
            total_dispatches: 10,
            holding_penalty_mins: 100.0,
            retention_penalty_mins: 50.0,
            total_lost_hours: 2.5,
          },
        ],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { result } = renderHook(() => useHoldingRetention(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('AVAILABLE');
    expect(result.current.data?.summary.total_dispatches).toBe(3532);
    expect(result.current.data?.summary.total_holding_penalty_mins).toBe(42142.0);
    expect(result.current.data?.summary.total_retention_penalty_mins).toBe(14490.0);
    expect(result.current.data?.summary.total_lost_hours).toBe(943.9);
    expect(result.current.data?.data[0].hour_label).toBe('00:00');
  });

  it('handles NO_OBSERVATIONS honest empty state', async () => {
    const mockEmptyResponse = {
      success: true,
      data: {
        success: true,
        status: 'NO_OBSERVATIONS',
        summary: {
          total_dispatches: 0,
          total_holding_penalty_mins: 0.0,
          total_retention_penalty_mins: 0.0,
          total_lost_hours: 0.0,
        },
        data: [],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEmptyResponse,
    } as Response);

    const { result } = renderHook(() => useHoldingRetention(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('NO_OBSERVATIONS');
    expect(result.current.data?.summary.total_dispatches).toBe(0);
    expect(result.current.data?.data).toEqual([]);
  });

  it('handles API error gracefully without mock fallbacks', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    } as Response);

    const { result } = renderHook(() => useHoldingRetention(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toContain('HTTP Error 500');
    expect(result.current.data).toBeNull();
  });
});
