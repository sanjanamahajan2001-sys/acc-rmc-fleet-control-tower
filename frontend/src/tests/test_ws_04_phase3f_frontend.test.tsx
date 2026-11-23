import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { SiteComparisonTableCard } from '../modules/operational_dashboard/components/SiteComparisonTableCard';
import { SiteComparisonDashboardPage } from '../modules/operational_dashboard/pages/SiteComparisonDashboardPage';
import { OverallDashboardPage } from '../modules/operational_dashboard/pages/OverallDashboardPage';
import { useSiteComparison } from '../modules/operational_dashboard/hooks/useSiteComparison';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

vi.mock('../modules/operational_dashboard/hooks/useSiteComparison');

describe('WS-04 Phase 3F Separate Dashboard Workspace & Non-Regression Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('WS04-F-01 / WS04-F-08: Site Comparison route renders SiteComparisonTableCard with required columns', () => {
    vi.mocked(useSiteComparison).mockReturnValue({
      data: {
        success: true,
        status: OperationalIntelligenceStatusEnum.AVAILABLE,
        data: [
          {
            rank: 1,
            site_code: 'ACC_VASCO',
            site_name: 'ACC VASCO',
            dispatches: 1174,
            volume_cum: 38755.0,
            avg_holding_mins: 18.5,
            avg_retention_mins: 7.5,
            max_queue_tms: 8,
            dispatch_accuracy: 70.0,
            status: 'Good',
          },
        ],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
      },
      loading: false,
      error: null,
      status: OperationalIntelligenceStatusEnum.AVAILABLE,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <SiteComparisonTableCard />
      </MemoryRouter>
    );

    expect(screen.getByText('SITE COMPARISON & BENCHMARKING')).toBeInTheDocument();
    expect(screen.getByText('ACC VASCO')).toBeInTheDocument();
    expect(screen.getByText('1174')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('WS04-F-02 / WS04-F-03 / WS04-F-04 / WS04-F-05 / WS04-F-06 / WS04-F-07: renders standalone SiteComparisonDashboardPage with clean header and exactly ONE filter strip', () => {
    vi.mocked(useSiteComparison).mockReturnValue({
      data: {
        success: true,
        status: OperationalIntelligenceStatusEnum.AVAILABLE,
        data: [],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY' },
      },
      loading: false,
      error: null,
      status: OperationalIntelligenceStatusEnum.AVAILABLE,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/site-comparison']}>
        <SiteComparisonDashboardPage />
      </MemoryRouter>
    );

    // Page identity
    expect(screen.getByText(/Site Comparison & Benchmarking Dashboard/i)).toBeInTheDocument();

    // ABSENT Overall Dashboard elements
    expect(screen.queryByText('Overall Operational Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Executive Fleet Command Tower, Operational SLAs & Customer Performance Intelligence')).not.toBeInTheDocument();
    expect(screen.queryByText('Dispatch Accuracy Score')).not.toBeInTheDocument();
    expect(screen.queryByText('Site Waiting Index')).not.toBeInTheDocument();
    expect(screen.queryByText('Dispatch Planning Index')).not.toBeInTheDocument();
    expect(screen.queryByText('Fleet Utilization Index')).not.toBeInTheDocument();

    // Exactly ONE filter strip / controls exist
    expect(screen.getAllByText(/Plant Selection/i).length).toBe(1);
    expect(screen.getAllByText(/Customer Filter/i).length).toBe(1);
    expect(screen.getAllByText(/Dataset Scope/i).length).toBe(1);
  });

  it('WS04-F-10: renders NO OBSERVATIONS state when synthetic scope V-05 is returned', () => {
    vi.mocked(useSiteComparison).mockReturnValue({
      data: {
        success: true,
        status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
        data: [],
        filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
      },
      loading: false,
      error: null,
      status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <SiteComparisonTableCard />
      </MemoryRouter>
    );

    expect(screen.getByText('NO OBSERVATIONS')).toBeInTheDocument();
  });

  it('WS04-F-11 / WS04-F-12: proves OverallDashboardPage is fully restored and does NOT contain WS-04 Site Comparison card', () => {
    render(
      <MemoryRouter initialEntries={['/overall-dashboard']}>
        <OverallDashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Overall Operational Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Site Comparison & Benchmarking Dashboard')).not.toBeInTheDocument();
  });
});
