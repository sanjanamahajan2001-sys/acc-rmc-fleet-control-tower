import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { DispatchAnalysisKPIRow2 } from '../modules/operational_dashboard/components/DispatchAnalysisKPIRow2';
import { useDispatchAnalysisKPIs } from '../modules/operational_dashboard/hooks/useDispatchAnalysisKPIs';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

vi.mock('../modules/operational_dashboard/hooks/useDispatchAnalysisKPIs');

describe('WS-05.4 Dispatch Analysis KPI Ribbon Row 2 Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders five Row 2 KPI cards with authoritative backend DTO values', () => {
    vi.mocked(useDispatchAnalysisKPIs).mockReturnValue({
      data: {
        total_dispatches: 3532,
        on_schedule_dispatches: 1802,
        sla_compliance_pct: 51.0,
        avg_interval_mins: 24.6,
        interval_variance_mins: 51.2,
        das_score_pct: 63.2,
        completed_dispatches: 3532,
        avg_loading_mins: 23.3,
        avg_transit_mins: 46.7,
        recommended_interval_mins: 20.9,
        cadence_status: 'Warning',
        potential_delay_reduction_hrs: 274.9,
      },
      status: OperationalIntelligenceStatusEnum.AVAILABLE,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <DispatchAnalysisKPIRow2 />
      </MemoryRouter>
    );

    expect(screen.getByText('COMPLETED DISPATCHES')).toBeInTheDocument();
    expect(screen.getByText('3,532')).toBeInTheDocument();

    expect(screen.getByText('AVG LOADING / TRANSIT')).toBeInTheDocument();
    expect(screen.getByText('23.3')).toBeInTheDocument();

    expect(screen.getByText('OPTIMIZED INTERVAL')).toBeInTheDocument();
    expect(screen.getByText('20.9 min')).toBeInTheDocument();

    expect(screen.getByText('CADENCE STATUS')).toBeInTheDocument();
    expect(screen.getByText('WARNING')).toBeInTheDocument();

    expect(screen.getByText('OPTIMIZATION IMPACT')).toBeInTheDocument();
    expect(screen.getByText('274.9')).toBeInTheDocument();
  });

  it('renders NO OBSERVATIONS empty state when dataset is empty', () => {
    vi.mocked(useDispatchAnalysisKPIs).mockReturnValue({
      data: null,
      status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <DispatchAnalysisKPIRow2 />
      </MemoryRouter>
    );

    expect(screen.getAllByText('NO OBSERVATIONS').length).toBeGreaterThan(0);
  });
});
