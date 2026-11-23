import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OverlapHeatMapCard } from '../modules/operational_dashboard/components/OverlapHeatMapCard';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const mockResponseGlobal = {
  success: true,
  data: {
    success: true,
    status: 'AVAILABLE',
    total_sites: 10,
    data: [
      {
        site_id: 'DEFAULT_CUSTOMER',
        site_name: 'DEFAULT_CUSTOMER',
        rank: 1,
        total_trips: 2066,
        peak_tms_together: 1874,
        avg_tms_standing_together: 906.0,
        overlap_hours: 47.3,
        weighted_tm_minutes: 2568865.6,
      },
      {
        site_id: 'CUST_RAJ_CHOPRA_N_COMPANY',
        site_name: 'CUST_RAJ_CHOPRA_N_COMPANY',
        rank: 2,
        total_trips: 58,
        peak_tms_together: 58,
        avg_tms_standing_together: 38.6,
        overlap_hours: 30.5,
        weighted_tm_minutes: 68787.9,
      },
      {
        site_id: 'CUST_NORBET_FERNANDES_MORJIM',
        site_name: 'CUST_NORBET_FERNANDES_MORJIM',
        rank: 3,
        total_trips: 58,
        peak_tms_together: 58,
        avg_tms_standing_together: 35.8,
        overlap_hours: 32.7,
        weighted_tm_minutes: 68120.4,
      },
      {
        site_id: 'CUST_ELIN_ELECTRONIC_LTD',
        site_name: 'CUST_ELIN_ELECTRONIC_LTD',
        rank: 4,
        total_trips: 54,
        peak_tms_together: 54,
        avg_tms_standing_together: 36.5,
        overlap_hours: 31.3,
        weighted_tm_minutes: 66638.1,
      },
    ],
    filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
  },
};

const mockResponseSyntheticEmpty = {
  success: true,
  data: {
    success: true,
    status: 'NO_OBSERVATIONS',
    total_sites: 0,
    data: [],
    filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
  },
};

describe('WS-03.2 Phase 3F Overlap Heat Map Frontend Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Constructs API request and renders Overlap Heat Map card with raw DTO metrics', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponseGlobal,
    } as any);

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <OverlapHeatMapCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Overlap Heat Map')).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining(`${env.VITE_API_BASE_URL}/operational-dashboard/overlap-heatmap'));

    expect(screen.getByText('DEFAULT_CUSTOMER')).toBeInTheDocument();
    expect(screen.getByText('CUST_RAJ_CHOPRA_N_COMPANY')).toBeInTheDocument();
    expect(screen.getByText('CUST_NORBET_FERNANDES_MORJIM')).toBeInTheDocument();
    expect(screen.queryByText('CUST_ELIN_ELECTRONIC_LTD')).not.toBeInTheDocument();

    expect(screen.getByText('906.0')).toBeInTheDocument();
    expect(screen.getByText('38.6')).toBeInTheDocument();
    expect(screen.getByText('47.3h')).toBeInTheDocument();
  });

  it('2. Renders honest empty NO_OBSERVATIONS state without fabricating rows for synthetic scope', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponseSyntheticEmpty,
    } as any);

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <OverlapHeatMapCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No overlap observations available for this scope.')).toBeInTheDocument();
    });

    expect(screen.queryByText('DEFAULT_CUSTOMER')).not.toBeInTheDocument();
  });

  it('3. Renders deterministic API error state when fetch fails', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error loading overlap data'));

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <OverlapHeatMapCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Network error loading overlap data')).toBeInTheDocument();
    });
  });

  it('4. Binds DTO peak TMs and total trips directly without React calculation', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponseGlobal,
    } as any);

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <OverlapHeatMapCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('1874')).toBeInTheDocument();
    });

    expect(screen.getByText('2,066')).toBeInTheDocument();
  });
});
