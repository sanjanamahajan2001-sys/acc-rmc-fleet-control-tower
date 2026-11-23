import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { DispatchCadenceTable } from '../modules/operational_dashboard/components/DispatchCadenceTable';
import { useDispatchCadence } from '../modules/operational_dashboard/hooks/useDispatchCadence';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

vi.mock('../modules/operational_dashboard/hooks/useDispatchCadence');

describe('WS-05.5 Dispatch Cadence Table Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders table headers and real DTO dispatch records', () => {
    vi.mocked(useDispatchCadence).mockReturnValue({
      data: [
        {
          dispatch_id: 'disp-1',
          dispatch_number: 'DISP-1001',
          dispatch_date: '2025-06-15',
          time_out: '08:00:00',
          time_in: '09:30:00',
          plant_code: 'ACC_VASCO',
          customer_code: 'CUST_AARA_HOTELS',
          customer_name: 'Aara Hotels',
          vehicle_id: 'GA04T9301',
          driver_name: 'Rajesh Kumar',
          interval_mins: 15.0,
          variance_mins: 0.0,
          holding_mins: 18.5,
          retention_mins: 7.5,
          sla_status: 'ON_SCHEDULE',
          trip_status: 'COMPLETED',
          cadence_recommendation: 'Maintain Cadence',
        },
      ],
      status: OperationalIntelligenceStatusEnum.AVAILABLE,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <DispatchCadenceTable />
      </MemoryRouter>
    );

    expect(screen.getByText('DISPATCH CADENCE & INTERVAL VARIANCE TABLE')).toBeInTheDocument();
    expect(screen.getByText('DISP-1001')).toBeInTheDocument();
    expect(screen.getByText('ACC_VASCO')).toBeInTheDocument();
    expect(screen.getByText('Aara Hotels')).toBeInTheDocument();
    expect(screen.getByText('GA04T9301')).toBeInTheDocument();
    expect(screen.getByText('ON_SCHEDULE')).toBeInTheDocument();
  });

  it('renders NO OBSERVATIONS empty state when dataset is empty', () => {
    vi.mocked(useDispatchCadence).mockReturnValue({
      data: [],
      status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <DispatchCadenceTable />
      </MemoryRouter>
    );

    expect(screen.getByText('NO OBSERVATIONS')).toBeInTheDocument();
  });
});
