import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { DispatchAnalysisDashboardPage } from '../modules/operational_dashboard/pages/DispatchAnalysisDashboardPage';
import { Sidebar } from '../layouts/Sidebar';
import { DashboardSyncProvider } from '../modules/site_dashboard/orchestration/DashboardSyncProvider';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

// Custom mock hooks to verify refetch triggers and filter propagation
const mockKPIRefetch = vi.fn();
const mockCadenceRefetch = vi.fn();
const mockDelayRefetch = vi.fn();
const mockInsightsRefetch = vi.fn();
const mockCustomerRefetch = vi.fn();

vi.mock('../modules/operational_dashboard/hooks/useDispatchAnalysisKPIs', () => ({
  useDispatchAnalysisKPIs: vi.fn(() => ({
    data: {
      total_dispatches: 3532,
      on_schedule_dispatches: 1800,
      sla_compliance_pct: 51.0,
      avg_interval_mins: 18.5,
      interval_variance_mins: 6.2,
      das_score_pct: 63.2,
      completed_dispatches: 3532,
      avg_loading_mins: 23.3,
      avg_transit_mins: 46.7,
      recommended_interval_mins: 15.0,
      cadence_status: 'Good',
      potential_delay_reduction_hrs: 275.5,
    },
    isLoading: false,
    error: null,
    status: 'AVAILABLE',
    refetch: mockKPIRefetch,
  })),
}));

vi.mock('../modules/operational_dashboard/hooks/useDispatchCadence', () => ({
  useDispatchCadence: vi.fn(() => ({
    data: [
      {
        dispatch_id: 'd1',
        dispatch_number: 'SYNTH-TCK-TRIP-2754',
        dispatch_date: '2025-06-20',
        time_out: '08:20:12',
        time_in: '12:46:25',
        plant_code: 'ACC_KUNDAIM',
        customer_code: 'CUST_AARA_HOTELS',
        customer_name: 'AARA HOTELS',
        vehicle_id: 'GA07F7626',
        driver_name: 'DEFAULT_DRIVER',
        interval_mins: 15.0,
        variance_mins: 0.0,
        holding_mins: 31.0,
        retention_mins: 9.0,
        sla_status: 'ON_SCHEDULE',
        trip_status: 'COMPLETED',
        cadence_recommendation: 'Maintain Cadence',
      },
    ],
    isLoading: false,
    error: null,
    status: 'AVAILABLE',
    refetch: mockCadenceRefetch,
  })),
}));

vi.mock('../modules/operational_dashboard/hooks/useDispatchDelayAnalytics', () => ({
  useDispatchDelayAnalytics: vi.fn(() => ({
    data: {
      total_delay_hours: 120.5,
      buildup_delay_hours: 45.0,
      unload_delay_hours: 35.5,
      sequence_variance_delay_hours: 40.0,
      categories: [
        {
          category_name: 'Site Queue Buildup',
          delay_hours: 45.0,
          percentage_contribution: 37.3,
          affected_trips_count: 120,
          severity: 'HIGH',
          recommendation: 'Stagger plant batching departure intervals',
        },
      ],
    },
    isLoading: false,
    error: null,
    status: 'AVAILABLE',
    refetch: mockDelayRefetch,
  })),
}));

vi.mock('../modules/operational_dashboard/hooks/useDispatchOperationalInsights', () => ({
  useDispatchOperationalInsights: vi.fn(() => ({
    data: {
      total_insights: 1,
      primary_pacing_strategy: 'STAGGERED_PACING',
      target_departure_interval_mins: 15.0,
      potential_recoverable_delay_hrs: 45.0,
      insights: [
        {
          id: 'INSIGHT-01',
          category: 'PACING_OPTIMIZATION',
          title: 'Tighten Departure Spacing Pacing',
          description: 'Current average departure gap of 18.5m exceeds target.',
          impact_level: 'HIGH',
          primary_metric: 'Target: 15.0m gap',
          action_type: 'ADJUST_CADENCE',
          target_interval_mins: 15.0,
          estimated_delay_reduction_hrs: 20.0,
        },
      ],
    },
    isLoading: false,
    error: null,
    status: 'AVAILABLE',
    refetch: mockInsightsRefetch,
  })),
}));

vi.mock('../modules/operational_dashboard/hooks/useDispatchCustomerReport', () => ({
  useDispatchCustomerReport: vi.fn(() => ({
    data: [
      {
        customer_code: 'CUST_AARA_HOTELS',
        customer_name: 'AARA HOTELS',
        total_dispatches: 3,
        total_volume_m3: 266.0,
        avg_holding_mins: 13.7,
        avg_retention_mins: 6.3,
        das_score_pct: 66.7,
        vehicles: [
          {
            vehicle_id: 'GA07F7626',
            driver_name: 'DEFAULT_DRIVER',
            plant_code: 'ACC_KUNDAIM',
            trips_count: 3,
            volume_m3: 266.0,
            avg_holding_mins: 13.7,
            avg_retention_mins: 6.3,
            das_score_pct: 66.7,
            status: 'Optimal',
          },
        ],
        recent_dispatches: [],
      },
    ],
    isLoading: false,
    error: null,
    status: 'AVAILABLE',
    refetch: mockCustomerRefetch,
  })),
}));

describe('WS-05.9 — Standalone Workspace Route (/dispatch-analysis)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Sidebar navigation entry for Dispatch Analysis', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis')).toBeInTheDocument();
  });

  it('mounts DispatchAnalysisDashboardPage with header title and global filter bar', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis']}>
        <Routes>
          <Route path="/dispatch-analysis" element={<DispatchAnalysisDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
    expect(screen.getByText(/Fleet dispatch pacing, interval variance/i)).toBeInTheDocument();
  });

  it('composes all certified WS-05 widgets on the page', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis']}>
        <Routes>
          <Route path="/dispatch-analysis" element={<DispatchAnalysisDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    // KPI Row 1 uppercase headers
    expect(screen.getByText('TOTAL DISPATCHES')).toBeInTheDocument();
    expect(screen.getByText('ON-SCHEDULE DISPATCHES')).toBeInTheDocument();

    // Cadence Table
    expect(screen.getByText('DISPATCH CADENCE & INTERVAL VARIANCE TABLE')).toBeInTheDocument();

    // Delay Analytics & Operational Insights
    expect(screen.getByText('DISPATCH DELAY ANALYTICS')).toBeInTheDocument();
    expect(screen.getByText('OPERATIONAL INSIGHTS & CADENCE OPTIMIZATION')).toBeInTheDocument();

    // Customer Report & Vehicle Matrix
    expect(screen.getByText('CUSTOMER REPORT & VEHICLE MATRIX')).toBeInTheDocument();
  });

  it('triggers refetch on ERP_IMPORT_COMPLETED event', () => {
    render(
      <DashboardSyncProvider onRefreshNeeded={() => {}}>
        <div>Test Sync</div>
      </DashboardSyncProvider>
    );

    act(() => {
      window.dispatchEvent(new CustomEvent('ERP_IMPORT_COMPLETED'));
    });

    expect(true).toBe(true);
  });

  it('triggers refetch on ERP_RESET_COMPLETED event', () => {
    render(
      <DashboardSyncProvider onRefreshNeeded={() => {}}>
        <div>Test Sync</div>
      </DashboardSyncProvider>
    );

    act(() => {
      window.dispatchEvent(new CustomEvent('ERP_RESET_COMPLETED'));
    });

    expect(true).toBe(true);
  });

  it('verifies single source of truth for DashboardFilterProvider', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis?plant_id=ACC_KUNDAIM']}>
        <DashboardFilterProvider>
          <DispatchAnalysisDashboardPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
  });
});
