import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { useCustomerEfficiency } from '../modules/operational_dashboard/hooks/useCustomerEfficiency';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <DashboardFilterProvider>{children}</DashboardFilterProvider>
  </MemoryRouter>
);

describe('WS-03.6 Phase 3F — useCustomerEfficiency Hook & DTO Binding', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Fetches customer efficiency data and binds DTO metrics without calculation', async () => {
    const mockResponse = {
      success: true,
      data: {
        success: true,
        status: 'AVAILABLE',
        data: [
          {
            rank: 1,
            customer_id: 'CUST_DAFTARY',
            customer_name: 'DAFTARY DESCON ENGG',
            cei_score: 0.0,
            grade: 'Critical',
            trend: 'FLAT',
            total_trips: 23,
            holding_penalty_mins: 859.0,
            retention_penalty_mins: 8.0,
          },
        ],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { result } = renderHook(() => useCustomerEfficiency(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('AVAILABLE');
    expect(result.current.data?.data.length).toBe(1);
    expect(result.current.data?.data[0].customer_id).toBe('CUST_DAFTARY');
    expect(result.current.data?.data[0].cei_score).toBe(0.0);
    expect(result.current.data?.data[0].grade).toBe('Critical');
    expect(result.current.data?.data[0].trend).toBe('FLAT');
  });

  it('2. Handles NO_OBSERVATIONS honest empty state without showing fake metrics', async () => {
    const mockEmptyResponse = {
      success: true,
      data: {
        success: true,
        status: 'NO_OBSERVATIONS',
        data: [],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEmptyResponse,
    } as Response);

    const { result } = renderHook(() => useCustomerEfficiency(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.status).toBe('NO_OBSERVATIONS');
    expect(result.current.data?.data.length).toBe(0);
  });
});
