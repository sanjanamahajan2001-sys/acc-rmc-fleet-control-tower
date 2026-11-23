import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TopProblemCustomersCard } from '../modules/operational_dashboard/components/TopProblemCustomersCard';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const mockResponseGlobal = {
  success: true,
  data: {
    success: true,
    status: 'AVAILABLE',
    total_count: 10,
    data: [
      {
        customer_id: 'DEFAULT_CUSTOMER',
        customer_name: 'DEFAULT_CUSTOMER',
        rank: 1,
        total_trips: 2066,
        holding_hours: 349.2,
        retention_hours: 100.0,
        total_lost_hours: 449.1,
        cei: 56.5,
      },
      {
        customer_id: 'CUST_RAJ_CHOPRA_N_COMPANY',
        customer_name: 'CUST_RAJ_CHOPRA_N_COMPANY',
        rank: 2,
        total_trips: 58,
        holding_hours: 24.5,
        retention_hours: 3.4,
        total_lost_hours: 27.9,
        cei: 3.9,
      },
      {
        customer_id: 'CUST_QUBIK_INFRA',
        customer_name: 'CUST_QUBIK_INFRA',
        rank: 3,
        total_trips: 42,
        holding_hours: 14.2,
        retention_hours: 4.4,
        total_lost_hours: 18.6,
        cei: 11.5,
      },
      {
        customer_id: 'CUST_CITYSCAPE_DEVELOPERS_GOGAL',
        customer_name: 'CUST_CITYSCAPE_DEVELOPERS_GOGAL',
        rank: 4,
        total_trips: 39,
        holding_hours: 9.3,
        retention_hours: 5.8,
        total_lost_hours: 15.1,
        cei: 22.6,
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
    total_count: 0,
    data: [],
    filters: { plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'SYNTHETIC_ONLY' },
  },
};

describe('WS-03.2 Phase 2F Top 10 Problem Customers Frontend Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders Top 3 preview card with raw DTO lost hours and CEI score', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponseGlobal,
    } as any);

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <TopProblemCustomersCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Top 10 Problem Customers')).toBeInTheDocument();
    });

    expect(screen.getByText('DEFAULT_CUSTOMER')).toBeInTheDocument();
    expect(screen.getByText('CUST_RAJ_CHOPRA_N_COMPANY')).toBeInTheDocument();
    expect(screen.getByText('CUST_QUBIK_INFRA')).toBeInTheDocument();
    expect(screen.queryByText('CUST_CITYSCAPE_DEVELOPERS_GOGAL')).not.toBeInTheDocument();

    expect(screen.getByText('449.1h')).toBeInTheDocument();
    expect(screen.getByText('56.5')).toBeInTheDocument();
  });

  it('opens production Drawer Overlay on "View all customers" click and displays all Top 10 records', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponseGlobal,
    } as any);

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <TopProblemCustomersCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Top 10 Problem Customers')).toBeInTheDocument();
    });

    const viewAllBtn = screen.getByText(/View all customers/i);
    fireEvent.click(viewAllBtn);

    await waitFor(() => {
      expect(screen.getByText('10 Total')).toBeInTheDocument();
    });

    expect(screen.getByText('CUST_CITYSCAPE_DEVELOPERS_GOGAL')).toBeInTheDocument();

    const closeBtn = screen.getByLabelText('Close Drawer');
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText('10 Total')).not.toBeInTheDocument();
    });
  });

  it('renders honest empty NO_OBSERVATIONS state without fabricating customer rows for synthetic scope', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponseSyntheticEmpty,
    } as any);

    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <TopProblemCustomersCard />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No customer observations available for this scope.')).toBeInTheDocument();
    });

    expect(screen.queryByText('DEFAULT_CUSTOMER')).not.toBeInTheDocument();
  });
});
