import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { usePotentialImpact } from '../modules/operational_dashboard/hooks/usePotentialImpact';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <DashboardFilterProvider>{children}</DashboardFilterProvider>
  </MemoryRouter>
);

describe('WS-03.5 Phase 3F — Potential Impact Frontend Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Fetches potential impact data and binds DTO metrics without calculation', async () => {
    const mockResponse = {
      success: true,
      data: {
        success: true,
        status: 'AVAILABLE',
        data: {
          holding_impact: { reduction_pct: 20.0, saved_hours_total: 140.5, trips_unlocked: 112 },
          retention_impact: { reduction_pct: 20.0, saved_hours_total: 48.3, trips_unlocked: 39 },
          total_impact: { saved_hours_total: 188.8, total_trips_unlocked: 151 },
        },
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { result } = renderHook(() => usePotentialImpact(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('AVAILABLE');
    expect(result.current.data?.data.holding_impact.saved_hours_total).toBe(140.5);
    expect(result.current.data?.data.holding_impact.trips_unlocked).toBe(112);
    expect(result.current.data?.data.retention_impact.saved_hours_total).toBe(48.3);
    expect(result.current.data?.data.retention_impact.trips_unlocked).toBe(39);
    expect(result.current.data?.data.total_impact.saved_hours_total).toBe(188.8);
    expect(result.current.data?.data.total_impact.total_trips_unlocked).toBe(151);
  });

  it('2. Handles NO_OBSERVATIONS honest empty state without showing fake metrics', async () => {
    const mockEmptyResponse = {
      success: true,
      data: {
        success: true,
        status: 'NO_OBSERVATIONS',
        data: {
          holding_impact: { reduction_pct: 20.0, saved_hours_total: 0.0, trips_unlocked: 0 },
          retention_impact: { reduction_pct: 20.0, saved_hours_total: 0.0, trips_unlocked: 0 },
          total_impact: { saved_hours_total: 0.0, total_trips_unlocked: 0 },
        },
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEmptyResponse,
    } as Response);

    const { result } = renderHook(() => usePotentialImpact(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('NO_OBSERVATIONS');
    expect(result.current.data?.data.total_impact.saved_hours_total).toBe(0.0);
    expect(result.current.data?.data.total_impact.total_trips_unlocked).toBe(0);
  });
});
