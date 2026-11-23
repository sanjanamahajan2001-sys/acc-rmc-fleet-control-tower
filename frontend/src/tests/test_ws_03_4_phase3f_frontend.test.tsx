import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { useDASOverview } from '../modules/operational_dashboard/hooks/useDASOverview';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <DashboardFilterProvider>{children}</DashboardFilterProvider>
  </MemoryRouter>
);

describe('WS-03.4 Phase 3F — useDASOverview Hook & DTO Binding', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Fetches DAS overview data and binds DTO metrics without calculation', async () => {
    const mockResponse = {
      success: true,
      data: {
        success: true,
        status: 'AVAILABLE',
        summary: {
          total_dispatches: 3532,
          accurate_dispatches: 2232,
          das_score: 63.2,
          target_sla: 90.0,
          variance: -26.8,
          operational_status: 'CRITICAL',
        },
        buckets: {
          within_20m_count: 2232,
          within_20m_pct: 63.2,
          moderate_20_40m_count: 674,
          moderate_20_40m_pct: 19.1,
          critical_above_40m_count: 626,
          critical_above_40m_pct: 17.7,
        },
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { result } = renderHook(() => useDASOverview(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('AVAILABLE');
    expect(result.current.data?.summary.total_dispatches).toBe(3532);
    expect(result.current.data?.summary.accurate_dispatches).toBe(2232);
    expect(result.current.data?.summary.das_score).toBe(63.2);
    expect(result.current.data?.summary.operational_status).toBe('CRITICAL');
    expect(result.current.data?.buckets.within_20m_pct).toBe(63.2);
    expect(result.current.data?.buckets.moderate_20_40m_pct).toBe(19.1);
    expect(result.current.data?.buckets.critical_above_40m_pct).toBe(17.7);
  });

  it('2. Handles NO_OBSERVATIONS honest empty state without showing fake score', async () => {
    const mockEmptyResponse = {
      success: true,
      data: {
        success: true,
        status: 'NO_OBSERVATIONS',
        summary: {
          total_dispatches: 0,
          accurate_dispatches: 0,
          das_score: null,
          target_sla: 90.0,
          variance: null,
          operational_status: 'NEUTRAL',
        },
        buckets: {
          within_20m_count: 0,
          within_20m_pct: 0.0,
          moderate_20_40m_count: 0,
          moderate_20_40m_pct: 0.0,
          critical_above_40m_count: 0,
          critical_above_40m_pct: 0.0,
        },
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEmptyResponse,
    } as Response);

    const { result } = renderHook(() => useDASOverview(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('NO_OBSERVATIONS');
    expect(result.current.data?.summary.total_dispatches).toBe(0);
    expect(result.current.data?.summary.das_score).toBeNull();
  });

  it('3. Handles API error gracefully without mock fallbacks', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    } as Response);

    const { result } = renderHook(() => useDASOverview(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toContain('HTTP Error 500');
    expect(result.current.data).toBeNull();
  });
});
