import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { OperationalInsightsWidget } from '../modules/operational_dashboard/components/OperationalInsightsWidget';
import { useDispatchOperationalInsights } from '../modules/operational_dashboard/hooks/useDispatchOperationalInsights';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

vi.mock('../modules/operational_dashboard/hooks/useDispatchOperationalInsights');

describe('WS-05.7 Operational Insights Widget Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders strategy banner and explainable operational insights cards', () => {
    vi.mocked(useDispatchOperationalInsights).mockReturnValue({
      data: {
        total_insights: 2,
        primary_pacing_strategy: 'STAGGERED_PACING',
        target_departure_interval_mins: 20.9,
        potential_recoverable_delay_hrs: 274.9,
        insights: [
          {
            id: 'INSIGHT-01',
            category: 'PACING_OPTIMIZATION',
            title: 'Tighten Departure Spacing Pacing',
            description: 'Current average departure gap of 24.6m exceeds calculated target cadence of 20.9m.',
            impact_level: 'HIGH',
            primary_metric: 'Target: 20.9m gap',
            action_type: 'ADJUST_CADENCE',
            target_interval_mins: 20.9,
            estimated_delay_reduction_hrs: 123.7,
          },
          {
            id: 'INSIGHT-02',
            category: 'PLANT_QUEUE_MITIGATION',
            title: 'Mitigate Plant Batching Queue Bottlenecks',
            description: 'Observed excess plant holding across dispatches.',
            impact_level: 'HIGH',
            primary_metric: '274.9h excess queue',
            action_type: 'RESTRUCTURE_BATCHING',
            target_interval_mins: 20.9,
            estimated_delay_reduction_hrs: 96.2,
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
        <OperationalInsightsWidget />
      </MemoryRouter>
    );

    expect(screen.getByText('OPERATIONAL INSIGHTS & CADENCE OPTIMIZATION')).toBeInTheDocument();
    expect(screen.getByText('STAGGERED PACING')).toBeInTheDocument();
    expect(screen.getByText('Tighten Departure Spacing Pacing')).toBeInTheDocument();
    expect(screen.getByText('Mitigate Plant Batching Queue Bottlenecks')).toBeInTheDocument();
  });

  it('renders NO OBSERVATIONS empty state when dataset is empty', () => {
    vi.mocked(useDispatchOperationalInsights).mockReturnValue({
      data: null,
      status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <OperationalInsightsWidget />
      </MemoryRouter>
    );

    expect(screen.getByText('NO OBSERVATIONS')).toBeInTheDocument();
  });
});
