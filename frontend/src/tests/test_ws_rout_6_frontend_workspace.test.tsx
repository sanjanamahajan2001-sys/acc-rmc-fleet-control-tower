import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DispatchAnalysisDashboardPage } from '../modules/operational_dashboard/pages/DispatchAnalysisDashboardPage';
import { RouteAnalysisWorkspace } from '../modules/operational_dashboard/components/RouteAnalysis/RouteAnalysisWorkspace';
import { RecommendationBanner } from '../modules/operational_dashboard/components/RouteAnalysis/RecommendationBanner';
import { CandidateComparisonMatrix } from '../modules/operational_dashboard/components/RouteAnalysis/CandidateComparisonMatrix';
import { DispatchRouteAnalysisOverviewTable } from '../modules/operational_dashboard/components/RouteAnalysis/DispatchRouteAnalysisOverviewTable';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';
import {
  RouteAnalysisSynthesisResult,
  CandidateComparisonItem,
  RouteAnalysisSnapshotItem,
} from '../modules/operational_dashboard/components/RouteAnalysis/routeAnalysis.types';

// Mock child widgets in Cadence view
vi.mock('../modules/operational_dashboard/components/DispatchAnalysisKPIRow1', () => ({
  DispatchAnalysisKPIRow1: () => <div data-testid="mock-kpi-row1">KPI Row 1</div>,
}));
vi.mock('../modules/operational_dashboard/components/DispatchAnalysisKPIRow2', () => ({
  DispatchAnalysisKPIRow2: () => <div data-testid="mock-kpi-row2">KPI Row 2</div>,
}));
vi.mock('../modules/operational_dashboard/components/DispatchCadenceTable', () => ({
  DispatchCadenceTable: () => <div data-testid="mock-cadence-table">Cadence Table</div>,
}));
vi.mock('../modules/operational_dashboard/components/DispatchDelayAnalyticsWidget', () => ({
  DispatchDelayAnalyticsWidget: () => <div data-testid="mock-delay-widget">Delay Widget</div>,
}));
vi.mock('../modules/operational_dashboard/components/OperationalInsightsWidget', () => ({
  OperationalInsightsWidget: () => <div data-testid="mock-insights-widget">Insights Widget</div>,
}));
vi.mock('../modules/operational_dashboard/components/CustomerVehicleReportWidget', () => ({
  CustomerVehicleReportWidget: () => <div data-testid="mock-customer-report">Customer Report</div>,
}));
vi.mock('../modules/site_dashboard/components/GlobalDashboardFilterBar', () => ({
  GlobalDashboardFilterBar: () => <div data-testid="mock-global-filter-bar">Filter Bar</div>,
}));
vi.mock('../modules/site_dashboard/components/SyncStatusHeaderBadge', () => ({
  SyncStatusHeaderBadge: () => <div data-testid="mock-sync-badge">Live Sync</div>,
}));

const mockComparisons: CandidateComparisonItem[] = [
  {
    plant_id: 'PLANT-A',
    plant_code: 'ALPHA',
    plant_name: 'Plant Alpha',
    is_current_source: true,
    is_recommended: false,
    is_viable: true,
    crow_fly_distance_km: 20.0,
    google_distance_km: 25.4,
    google_duration_in_traffic_mins: 42.0,
    google_static_duration_mins: 38.0,
    google_traffic_delay_mins: 4.0,
    historical_t1_p50_mins: 45.0,
    historical_t1_p25_mins: 40.0,
    historical_t1_p75_mins: 50.0,
    historical_t1_iqr_mins: 10.0,
    historical_sample_count: 50,
    historical_confidence: 'HIGH',
    historical_winner_status: 'CURRENT',
  },
  {
    plant_id: 'PLANT-B',
    plant_code: 'BETA',
    plant_name: 'Plant Beta',
    is_current_source: false,
    is_recommended: true,
    is_viable: true,
    crow_fly_distance_km: 15.0,
    google_distance_km: 18.2,
    google_duration_in_traffic_mins: 28.0,
    google_static_duration_mins: 25.0,
    google_traffic_delay_mins: 3.0,
    historical_t1_p50_mins: 30.0,
    historical_t1_p25_mins: 27.0,
    historical_t1_p75_mins: 32.0,
    historical_t1_iqr_mins: 5.0,
    historical_sample_count: 80,
    historical_confidence: 'HIGH',
    historical_winner_status: 'WINNER',
  },
];

const mockSynthesisResult: RouteAnalysisSynthesisResult = {
  analysis_id: 'mock-analysis-12345678',
  site_id: 'SITE-001',
  site_code: 'SITE-BLR-01',
  site_name: 'Metropolitan Infrastructure Project',
  current_source_plant_id: 'PLANT-A',
  current_source_plant_code: 'ALPHA',
  current_source_plant_name: 'Plant Alpha',
  recommended_plant_id: 'PLANT-B',
  recommended_plant_code: 'BETA',
  recommended_plant_name: 'Plant Beta',
  recommendation_status: 'RECOMMEND_ALTERNATIVE',
  primary_case_category: 'C3_TRAFFIC_OVERRIDE_ALT',
  is_traffic_override: true,
  decision_reason_summary: 'Alternative Plant Beta saves 14.0 mins in live Google traffic and 15.0 mins in historical T1 transit.',
  minutes_saved: 14.0,
  engine_version: '1.2.1',
  policy_version: '1.2.1',
  analysis_mode: 'NOW',
  requested_departure_time: null,
  analysis_timestamp: '2026-09-08T11:00:00Z',
  is_google_fresh: true,
  is_google_stale_cache: false,
  google_cache_age_seconds: 45,
  is_historical_sufficient: true,
  comparisons: mockComparisons,
  historical_evidence: {
    case_category: 'C3',
    is_overall_sufficient: true,
  },
  google_evidence: {
    provider: 'Google Routes API v2',
    is_live: true,
  },
};

const mockSnapshotList: RouteAnalysisSnapshotItem[] = [
  {
    analysis_id: 'snap-001-alt-winner',
    customer_id: 'CUST-01',
    customer_name: 'Metropolitan Builders',
    customer_code: 'CUST_METRO',
    site_id: 'SITE-001',
    site_name: 'Tower Site One',
    site_code: 'SITE_TOWER_1',
    current_source_plant_id: 'PLANT-A',
    current_source_plant_name: 'Plant Alpha',
    current_source_plant_code: 'ALPHA',
    recommended_plant_id: 'PLANT-B',
    recommended_plant_name: 'Plant Beta',
    recommended_plant_code: 'BETA',
    recommendation_status: 'RECOMMEND_ALTERNATIVE',
    primary_case_category: 'C3_TRAFFIC_OVERRIDE_ALT',
    failure_reason_code: null,
    analysis_mode: 'NOW',
    planned_departure_time: null,
    engine_version: '1.2.1',
    policy_version: '1.2.1',
    decision_reason_summary: 'Plant Beta saves 14.0 mins in traffic.',
    minutes_saved: 14.0,
    analysis_context: 'ROUTINE',
    operator_notes: null,
    erp_import_batch_id: 'e8be73b4-983a-449f-8c78-74226a35c917',
    data_freshness_seconds: 45,
    is_cached_result: false,
    queried_at: '2026-09-08T11:00:00Z',
  },
  {
    analysis_id: 'snap-002-retain-curr',
    customer_id: 'CUST-02',
    customer_name: 'Apex Infrastructure',
    customer_code: 'CUST_APEX',
    site_id: 'SITE-002',
    site_name: 'Bridge Site North',
    site_code: 'SITE_BRIDGE',
    current_source_plant_id: 'PLANT-A',
    current_source_plant_name: 'Plant Alpha',
    current_source_plant_code: 'ALPHA',
    recommended_plant_id: 'PLANT-A',
    recommended_plant_name: 'Plant Alpha',
    recommended_plant_code: 'ALPHA',
    recommendation_status: 'RECOMMEND_CURRENT_SOURCE',
    primary_case_category: 'C1_BOTH_AGREE_CURRENT',
    failure_reason_code: null,
    analysis_mode: 'NOW',
    planned_departure_time: null,
    engine_version: '1.2.1',
    policy_version: '1.2.1',
    decision_reason_summary: 'Plant Alpha is optimal in both traffic and history.',
    minutes_saved: 0.0,
    analysis_context: 'ROUTINE',
    operator_notes: null,
    erp_import_batch_id: 'e8be73b4-983a-449f-8c78-74226a35c917',
    data_freshness_seconds: 120,
    is_cached_result: true,
    queried_at: '2026-09-08T10:50:00Z',
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <DashboardFilterProvider>{children}</DashboardFilterProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
};

describe('WS-ROUT-6: Route Analysis Frontend Workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/dispatch-analysis/route-analysis/batch-context')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: {
              batch_id: 'e8be73b4-983a-449f-8c78-74226a35c917',
              total_erp_dispatches: 5,
              unique_route_corridors: 2,
              analyzed_snapshots: 2,
              alt_recommended_count: 1,
              retain_approved_count: 1,
              no_difference_count: 1,
              location_missing_count: 0,
              live_only_count: 0,
            }
          }),
        });
      }
      if (url.includes('/dispatch-analysis/route-analysis/history')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockSnapshotList, total_count: 2 }),
        });
      }
      if (url.includes('/dispatch-analysis/route-analysis/snapshot/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockSynthesisResult }),
        });
      }
      if (url.includes('/dispatch-analysis/route-analysis/evaluate') || url.includes('/dispatch-analysis/route-analysis')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockSynthesisResult }),
        });
      }
      if (url.includes('/dispatch-analysis/sites') || url.includes('/sites')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: [
                { id: 'SITE-001', code: 'SITE_TOWER_1', name: 'Tower Site One', latitude: 15.45, longitude: 73.85 },
              ],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: {} }),
      });
    });
  });

  it('renders tab switchers inside DispatchAnalysisDashboardPage and switches to Route Analysis workspace', async () => {
    render(<DispatchAnalysisDashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('mock-kpi-row1')).toBeInTheDocument();
    expect(screen.getByTestId('tab-dispatch-cadence')).toBeInTheDocument();
    expect(screen.getByTestId('tab-route-analysis')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('tab-route-analysis'));

    await waitFor(() => {
      expect(screen.getByTestId('route-analysis-decision-workspace')).toBeInTheDocument();
      expect(screen.getByText('Route Analysis Decision Support Engine')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('mock-kpi-row1')).not.toBeInTheDocument();
  });

  it('renders overview table with snapshot history and summary KPIs', async () => {
    const { container } = render(<RouteAnalysisWorkspace />, { wrapper: createWrapper() });

    // Wait for snapshot list item
    await waitFor(() => {
      expect(screen.getByTestId('btn-view-analysis-snap-001-alt-winner')).toBeInTheDocument();
    }, { timeout: 4000 });

    expect(screen.getByText('Tower Site One')).toBeInTheDocument();
    expect(screen.getByText('Bridge Site North')).toBeInTheDocument();
    expect(screen.getByText(/Dispatches Analyzed/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Alt Recommended/i).length).toBeGreaterThanOrEqual(1);
  });

  it('navigates to detail view when clicking View Analysis and back to overview', async () => {
    render(<RouteAnalysisWorkspace />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('btn-view-analysis-snap-001-alt-winner')).toBeInTheDocument();
    });

    // Click View Analysis
    fireEvent.click(screen.getByTestId('btn-view-analysis-snap-001-alt-winner'));

    // Detail view should render
    await waitFor(() => {
      expect(screen.getByTestId('btn-back-to-overview')).toBeInTheDocument();
      expect(screen.getByTestId('recommendation-banner')).toBeInTheDocument();
      expect(screen.getByText(/RECOMMEND ALTERNATIVE PLANT/i)).toBeInTheDocument();
    });

    // Click Back to Overview
    fireEvent.click(screen.getByTestId('btn-back-to-overview'));

    await waitFor(() => {
      expect(screen.getByText('Dispatches Analyzed')).toBeInTheDocument();
    });
  });

  it('supports NOW vs PLANNED evaluation mode toggle', async () => {
    render(<RouteAnalysisWorkspace />, { wrapper: createWrapper() });

    const nowButton = screen.getByText(/Current Traffic \(NOW\)/i);
    const plannedButton = screen.getByText(/Planned Departure/i);

    expect(nowButton).toBeInTheDocument();
    expect(plannedButton).toBeInTheDocument();

    fireEvent.click(plannedButton);
    expect(plannedButton).toHaveClass('bg-white');

    fireEvent.click(nowButton);
    expect(nowButton).toHaveClass('bg-white');
  });

  it('renders CandidateComparisonMatrix correctly with ERP T1 stats and Google traffic stats', () => {
    render(
      <CandidateComparisonMatrix
        comparisons={mockComparisons}
        recommendedPlantId="PLANT-B"
        currentPlantId="PLANT-A"
      />
    );

    expect(screen.getByText('Plant Alpha')).toBeInTheDocument();
    expect(screen.getByText('Plant Beta')).toBeInTheDocument();
    expect(screen.getByText('Current Plant')).toBeInTheDocument();
    expect(screen.getByText('Recommended Plant')).toBeInTheDocument();
    expect(screen.getByText('45.0m')).toBeInTheDocument();
    expect(screen.getByText('30.0m')).toBeInTheDocument();
    expect(screen.getByText('42.0m')).toBeInTheDocument();
    expect(screen.getByText('28.0m')).toBeInTheDocument();
  });

  it('renders RecommendationBanner with correct styling and decision text for C3 RECOMMEND_ALTERNATIVE', () => {
    render(<RecommendationBanner result={mockSynthesisResult} />);

    expect(screen.getByTestId('recommendation-banner')).toBeInTheDocument();
    expect(screen.getByText(/RECOMMEND ALTERNATIVE PLANT/i)).toBeInTheDocument();
    expect(screen.getByText(/Case: C3 TRAFFIC OVERRIDE ALT/i)).toBeInTheDocument();
    expect(screen.getByText(/Alternative Plant Beta saves 14.0 mins/i)).toBeInTheDocument();
  });
});
