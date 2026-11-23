import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalDashboardShell } from '../modules/operational_dashboard/shell/OperationalDashboardShell';
import { DispatchAccuracyCard } from '../modules/operational_dashboard/components/DispatchAccuracyCard';
import { KPIStatusEnum, AvailabilityEnum } from '../modules/operational_dashboard/hooks/useExecutiveKPIs';

describe('WS-03.1 Phase 2F Dispatch Accuracy Frontend Tests', () => {
  it('1. Renders Dispatch Accuracy card with backend-provided real value and status', () => {
    render(
      <DispatchAccuracyCard
        data={{
          key: 'accuracy',
          label: 'Dispatch Accuracy',
          current_value: 63.2,
          unit: '%',
          target: 90.0,
          variance: -26.8,
          status: KPIStatusEnum.CRITICAL,
          availability: AvailabilityEnum.AVAILABLE,
        }}
      />
    );

    expect(screen.getByText('Dispatch Accuracy')).toBeInTheDocument();
    expect(screen.getByText('63.2')).toBeInTheDocument();
    expect(screen.getByText('%')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('-26.8%')).toBeInTheDocument();
  });

  it('2. Renders honest NO_OBSERVATIONS state when current_value is null', () => {
    render(
      <DispatchAccuracyCard
        data={{
          key: 'accuracy',
          label: 'Dispatch Accuracy',
          current_value: null,
          unit: '%',
          target: 90.0,
          variance: null,
          status: KPIStatusEnum.NEUTRAL,
          availability: AvailabilityEnum.NO_OBSERVATIONS,
        }}
      />
    );

    expect(screen.getByText('Dispatch Accuracy')).toBeInTheDocument();
    expect(screen.getByText('N/A')).toBeInTheDocument();
    expect(screen.getByText('NO OBSERVATIONS')).toBeInTheDocument();
    expect(screen.getByText('NEUTRAL')).toBeInTheDocument();
  });

  it('3. Verifies Executive Top Ribbon integration inside OperationalDashboardShell', async () => {
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
                swi: { key: 'swi', label: 'Site Waiting Index', current_value: null, unit: '/100', status: 'NEUTRAL', availability: 'AVAILABLE' },
                dpi: { key: 'dpi', label: 'Dispatch Planning Index', current_value: null, unit: '/100', status: 'NEUTRAL', availability: 'AVAILABLE' },
                fui: { key: 'fui', label: 'Fleet Utilization Index', current_value: null, unit: '/100', status: 'NEUTRAL', availability: 'AVAILABLE' },
                total_dispatches: { key: 'total_dispatches', label: 'Total Dispatches', current_value: null, unit: 'Trips', status: 'NEUTRAL', availability: 'SOURCE_UNAVAILABLE' },
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
      expect(screen.getByText('63.2')).toBeInTheDocument();
    });
  });
});
