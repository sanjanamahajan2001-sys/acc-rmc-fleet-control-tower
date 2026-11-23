import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { CustomerVehicleReportWidget } from '../modules/operational_dashboard/components/CustomerVehicleReportWidget';
import { useDispatchCustomerReport } from '../modules/operational_dashboard/hooks/useDispatchCustomerReport';
import { OperationalIntelligenceStatusEnum } from '../modules/operational_dashboard/hooks/useTopProblemCustomers';

vi.mock('../modules/operational_dashboard/hooks/useDispatchCustomerReport');

describe('WS-05.8 Customer Vehicle Report Widget Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders customer summary and vehicle matrix with real DTO data', () => {
    vi.mocked(useDispatchCustomerReport).mockReturnValue({
      data: [
        {
          customer_code: 'CUST_AARA_HOTELS',
          customer_name: 'Aara Hotels',
          total_dispatches: 3,
          total_volume_m3: 18.0,
          avg_holding_mins: 13.7,
          avg_retention_mins: 6.3,
          das_score_pct: 100.0,
          vehicles: [
            {
              vehicle_id: 'GA04T9302',
              driver_name: 'Suresh Naik',
              plant_code: 'ACC_KUNDAIM',
              trips_count: 3,
              volume_m3: 18.0,
              avg_holding_mins: 13.7,
              avg_retention_mins: 6.3,
              das_score_pct: 100.0,
              status: 'Optimal',
            },
          ],
          recent_dispatches: [],
        },
      ],
      status: OperationalIntelligenceStatusEnum.AVAILABLE,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <CustomerVehicleReportWidget />
      </MemoryRouter>
    );

    expect(screen.getByText('CUSTOMER REPORT & VEHICLE MATRIX')).toBeInTheDocument();
    expect(screen.getByText('Aara Hotels')).toBeInTheDocument();
    expect(screen.getByText('(CUST_AARA_HOTELS)')).toBeInTheDocument();
    expect(screen.getByText('GA04T9302')).toBeInTheDocument();
    expect(screen.getByText('Suresh Naik')).toBeInTheDocument();
    expect(screen.getByText('ACC_KUNDAIM')).toBeInTheDocument();
    expect(screen.getAllByText('100.0%').length).toBeGreaterThan(0);
  });

  it('renders NO OBSERVATIONS empty state when dataset is empty', () => {
    vi.mocked(useDispatchCustomerReport).mockReturnValue({
      data: [],
      status: OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <CustomerVehicleReportWidget />
      </MemoryRouter>
    );

    expect(screen.getByText('NO OBSERVATIONS')).toBeInTheDocument();
  });
});
