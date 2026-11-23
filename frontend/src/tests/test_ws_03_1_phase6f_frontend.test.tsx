import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalDashboardShell } from '../modules/operational_dashboard/shell/OperationalDashboardShell';
import { TotalDispatchesCard } from '../modules/operational_dashboard/components/TotalDispatchesCard';
import { KPIStatusEnum, AvailabilityEnum } from '../modules/operational_dashboard/hooks/useExecutiveKPIs';

describe('WS-03.1 Phase 6F Total Dispatches Frontend Tests', () => {
  it('1. Renders Total Dispatches card with backend count, NEUTRAL status, and Volume Source Unavailable', () => {
    render(
      <TotalDispatchesCard
        data={{
          key: 'total_dispatches',
          label: 'Total Dispatches',
          current_value: 3532.0,
          unit: 'Trips',
          target: null,
          variance: null,
          total_volume_m3: null,
          status: KPIStatusEnum.NEUTRAL,
          availability: AvailabilityEnum.AVAILABLE,
        }}
      />
    );

    expect(screen.getByText('Total Dispatches')).toBeInTheDocument();
    expect(screen.getByText('3,532')).toBeInTheDocument();
    expect(screen.getByText('Trips')).toBeInTheDocument();
    expect(screen.getByText('NEUTRAL')).toBeInTheDocument();
    expect(screen.getByText(/N\/A \(Source Unavailable\)/i)).toBeInTheDocument();
    expect(screen.getByText('Target:')).toBeInTheDocument();
  });

  it('2. Renders 0 dispatches count honestly for synthetic scope without converting to N/A', () => {
    render(
      <TotalDispatchesCard
        data={{
          key: 'total_dispatches',
          label: 'Total Dispatches',
          current_value: 0.0,
          unit: 'Trips',
          target: null,
          variance: null,
          total_volume_m3: null,
          status: KPIStatusEnum.NEUTRAL,
          availability: AvailabilityEnum.AVAILABLE,
        }}
      />
    );

    expect(screen.getByText('Total Dispatches')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('NEUTRAL')).toBeInTheDocument();
  });

  it('3. Verifies Total Dispatches card mounts in Position 5 of Executive Top Ribbon inside OperationalDashboardShell', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes(`${env.VITE_API_BASE_URL}/operational-dashboard/kpis')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              context: {
                dataset_id: 'DS-20260805-001',
                snapshot_version: 'v2.11-SNAP-20260805',
                operational_date: '2026-08-05',
                plant_id: 'ALL',
                customer_id: 'ALL',
                dataset_type: 'REAL_ONLY',
                generated_at: '2026-08-12T00:00:00Z',
              },
              kpis: {
                dispatch_accuracy: {
                  key: 'accuracy',
                  label: 'Dispatch Accuracy',
                  current_value: 63.2,
                  unit: '%',
                  target: 90.0,
                  variance: -26.8,
                  status: 'CRITICAL',
                  availability: 'AVAILABLE',
                },
                swi: {
                  key: 'swi',
                  label: 'Site Waiting Index',
                  current_value: 46.6,
                  unit: '/100',
                  target: 75.0,
                  variance: -28.4,
                  status: 'CRITICAL',
                  availability: 'AVAILABLE',
                },
                dpi: {
                  key: 'dpi',
                  label: 'Dispatch Planning Index',
                  current_value: 8.2,
                  unit: '/100',
                  target: 85.0,
                  variance: -76.8,
                  status: 'CRITICAL',
                  availability: 'AVAILABLE',
                },
                fui: {
                  key: 'fui',
                  label: 'Fleet Utilization Index',
                  current_value: 100.0,
                  unit: '/100',
                  target: 70.0,
                  variance: 30.0,
                  status: 'OPTIMAL',
                  availability: 'AVAILABLE',
                },
                total_dispatches: {
                  key: 'total_dispatches',
                  label: 'Total Dispatches',
                  current_value: 3532.0,
                  unit: 'Trips',
                  target: null,
                  variance: null,
                  total_volume_m3: null,
                  status: 'NEUTRAL',
                  availability: 'AVAILABLE',
                },
              },
            },
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            context: { dataset_id: 'DS-1', plant_id: 'ALL', customer_id: 'ALL', dataset_type: 'REAL_ONLY', operational_date: '2026-08-05' },
            metadata: { total_dispatches: 3532, dataset_status: 'ACTIVE_PRODUCTION', sync_status: 'SYNCHRONIZED' },
            available_plants: [{ id: 'ALL', name: 'All Plants' }],
            available_customers: [{ id: 'ALL', name: 'All Customers' }],
          },
        }),
      });
    });

    render(
      <MemoryRouter initialEntries={['/overall-dashboard']}>
        <DashboardFilterProvider>
          <Routes>
            <Route path="/overall-dashboard" element={<OperationalDashboardShell />} />
          </Routes>
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('executive-kpi-ribbon')).toBeInTheDocument();
      expect(screen.getByTestId('dispatch-accuracy-card')).toBeInTheDocument();
      expect(screen.getByTestId('site-waiting-index-card')).toBeInTheDocument();
      expect(screen.getByTestId('dispatch-planning-index-card')).toBeInTheDocument();
      expect(screen.getByTestId('fleet-utilization-index-card')).toBeInTheDocument();
      expect(screen.getByTestId('total-dispatches-card')).toBeInTheDocument();
      expect(screen.getByText('3,532')).toBeInTheDocument();
    });
  });
});
