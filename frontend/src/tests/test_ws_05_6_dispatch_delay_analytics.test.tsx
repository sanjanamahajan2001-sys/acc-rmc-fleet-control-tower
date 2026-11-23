import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { DispatchDelayAnalyticsWidget } from '../modules/operational_dashboard/components/DispatchDelayAnalyticsWidget';
import { useDispatchDelayAnalytics } from '../modules/operational_dashboard/hooks/useDispatchDelayAnalytics';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

vi.mock('../modules/operational_dashboard/hooks/useDispatchDelayAnalytics');

describe('WS-05.6 Dispatch Delay Analytics Widget Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders delay analytics summary bars, chart, and categories', () => {
    vi.mocked(useDispatchDelayAnalytics).mockReturnValue({
      data: {
        total_delay_hours: 1374.5,
        buildup_delay_hours: 194.3,
        unload_delay_hours: 18.2,
        sequence_variance_delay_hours: 1162.0,
        categories: [
          {
            category_name: 'Site Queue Buildup',
            delay_hours: 194.3,
            percentage_contribution: 14.1,
            affected_trips_count: 1318,
            severity: 'HIGH',
            recommendation: 'Stagger plant batching departure intervals',
          },
          {
            category_name: 'Unload Sign-off Delay',
            delay_hours: 18.2,
            percentage_contribution: 1.3,
            affected_trips_count: 518,
            severity: 'HIGH',
            recommendation: 'Enforce 10-minute customer retention SLA',
          },
          {
            category_name: 'Sequence Variance Delay',
            delay_hours: 1162.0,
            percentage_contribution: 84.5,
            affected_trips_count: 1730,
            severity: 'HIGH',
            recommendation: 'Standardize departure gap to 12–15 minutes',
          },
        ],
      },
      status: OperationalIntelligenceStatusEnum.AVAILABLE,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <DispatchDelayAnalyticsWidget />
      </MemoryRouter>
    );

    expect(screen.getByText('DISPATCH DELAY ANALYTICS')).toBeInTheDocument();
    expect(screen.getByText('Site Queue Buildup')).toBeInTheDocument();
    expect(screen.getByText('Unload Sign-off Delay')).toBeInTheDocument();
    expect(screen.getByText('Sequence Variance Delay')).toBeInTheDocument();
  });

  it('renders NO OBSERVATIONS empty state when dataset is empty', () => {
    vi.mocked(useDispatchDelayAnalytics).mockReturnValue({
      data: null,
      status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <DispatchDelayAnalyticsWidget />
      </MemoryRouter>
    );

    expect(screen.getByText('NO OBSERVATIONS')).toBeInTheDocument();
  });
});
