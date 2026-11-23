import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardFilterProvider, useDashboardFilters } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

const TestComponent = () => {
  const { customerOptions, filters } = useDashboardFilters();
  return (
    <div>
      <span data-testid="selected-customer">{filters.customer_id}</span>
      <ul data-testid="customer-options">
        {customerOptions.map((c) => (
          <li key={c.id} data-testid={`customer-option-${c.id}'}>
            {c.name} ({c.code})
          </li>
        ))}
      </ul>
    </div>
  );
};

describe('Phase 4B.6 — DashboardFilterProvider & Global Filter Propagation Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Initial Load & Effective Display Resolution: Renders effective customer display names', async () => {
    const mockFilterData = {
      success: true,
      data: {
        plants: [{ id: 'ALL', name: 'All Plants' }, { id: 'ACC_VASCO', name: 'ACC VASCO' }],
        customers: [
          { id: 'ALL', name: 'All Customers', code: 'ALL' },
          { id: 'CUST_LNT', name: 'Larsen & Toubro Goa Infrastructure', code: 'CUST_LNT', raw_customer_name: 'L&T CONSTRUCTIONS GOA', effective_customer_name: 'Larsen & Toubro Goa Infrastructure' },
          { id: 'CUST_ACC', name: 'ACC CONCRETE SUPPLIES', code: 'CUST_ACC', raw_customer_name: 'ACC CONCRETE SUPPLIES', effective_customer_name: 'ACC CONCRETE SUPPLIES' },
        ],
        dataset_info: {
          operational_date: '2026-08-05',
          dataset_id: 'DS-20260805-001',
          import_timestamp: new Date().toISOString(),
          calculation_timestamp: new Date().toISOString(),
          total_dispatches: 3532,
          total_trips: 3532,
          dataset_status: 'ACTIVE_PRODUCTION',
        },
      },
    };

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockFilterData,
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DashboardFilterProvider>
          <TestComponent />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('customer-option-CUST_LNT')).toHaveTextContent('Larsen & Toubro Goa Infrastructure (CUST_LNT)');
      expect(screen.getByTestId('customer-option-CUST_ACC')).toHaveTextContent('ACC CONCRETE SUPPLIES (CUST_ACC)');
    });
  });

  it('2. Event-Driven Refetch: Updates customer display label upon fleet-settings-updated CustomEvent', async () => {
    let callCount = 0;
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters')) {
        callCount++;
        const name = callCount === 1 ? 'Original Customer Name' : 'Updated Effective Customer Name';
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              plants: [{ id: 'ALL', name: 'All Plants' }],
              customers: [
                { id: 'ALL', name: 'All Customers', code: 'ALL' },
                { id: 'CUST_001', name, code: 'CUST_001' },
              ],
            },
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DashboardFilterProvider>
          <TestComponent />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('customer-option-CUST_001')).toHaveTextContent('Original Customer Name');
    });

    // Trigger CustomEvent
    act(() => {
      window.dispatchEvent(new CustomEvent('fleet-settings-updated'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('customer-option-CUST_001')).toHaveTextContent('Updated Effective Customer Name');
    });
  });
});
