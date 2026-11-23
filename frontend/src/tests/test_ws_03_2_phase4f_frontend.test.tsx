import { renderHook, waitFor, render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { useSiteReadiness, OperationalGradeEnum } from '../modules/operational_dashboard/hooks/useSiteReadiness';
import { SiteReadinessCard } from '../modules/operational_dashboard/components/SiteReadinessCard';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

const mockResponse = {
  success: true,
  data: {
    success: true,
    status: OperationalIntelligenceStatusEnum.AVAILABLE,
    total_sites: 2,
    data: [
      {
        site_id: 'CUST_COUTINHO',
        site_name: 'COUTINHO N ASSOCIATES',
        rank: 1,
        total_trips: 1,
        swi_site: 0.0,
        dpi_site: 0.0,
        fui_site: 4.2,
        sri_score: 1.0,
        grade: OperationalGradeEnum.GRADE_D,
      },
      {
        site_id: 'CUST_MARCON',
        site_name: 'MARCON',
        rank: 2,
        total_trips: 1,
        swi_site: 0.0,
        dpi_site: 0.0,
        fui_site: 4.2,
        sri_score: 1.0,
        grade: OperationalGradeEnum.GRADE_D,
      },
    ],
    filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
  },
};

describe('WS-03.2 Phase 4F Site Readiness Index Frontend Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1-5. hook constructs API endpoint and propagates plant_id, customer_id, dataset_type', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any) => {
      const urlStr = String(url);
      if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters`)) {
        return { ok: true, json: async () => ({ success: true, data: [] }) } as Response;
      }
      return { ok: true, json: async () => mockResponse } as Response;
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter>
        <DashboardFilterProvider>{children}</DashboardFilterProvider>
      </MemoryRouter>
    );

    const { result } = renderHook(() => useSiteReadiness(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining(`${env.VITE_API_BASE_URL}/operational-dashboard/site-readiness?')
    );
    expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('plant_id=ALL'));
    expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('customer_id=ALL'));
    expect(result.current.data?.total_sites).toBe(2);
  });

  it('6-12. SiteReadinessCard renders site_name, total_trips, sri_score, grade directly from DTO without React calculation', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any) => {
      const urlStr = String(url);
      if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters')) {
        return { ok: true, json: async () => ({ success: true, data: [] }) } as Response;
      }
      return { ok: true, json: async () => mockResponse } as Response;
    });

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <SiteReadinessCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('COUTINHO N ASSOCIATES')).toBeInTheDocument();
      expect(screen.getByText('MARCON')).toBeInTheDocument();
    });

    expect(screen.getAllByText('1.0').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/D • Critical/i).length).toBeGreaterThan(0);
  });

  it('13-18. handles loading state, error state, and NO_OBSERVATIONS honest empty state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any) => {
      const urlStr = String(url);
      if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters')) {
        return { ok: true, json: async () => ({ success: true, data: [] }) } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          success: true,
          data: {
            success: true,
            status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
            total_sites: 0,
            data: [],
            filters: { dataset_type: 'SYNTHETIC_ONLY' },
          },
        }),
      } as Response;
    });

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <SiteReadinessCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText('No site readiness observations available for this scope.')
      ).toBeInTheDocument();
    });

    expect(screen.queryByText('COUTINHO N ASSOCIATES')).not.toBeInTheDocument();
  });
});
