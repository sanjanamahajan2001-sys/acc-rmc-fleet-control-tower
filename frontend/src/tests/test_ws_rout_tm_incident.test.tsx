import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TMIncidentAccessWorkspace } from '../modules/operational_dashboard/components/RouteAnalysis/TMIncidentAccessWorkspace';

// Mock RouteMapVisualization
vi.mock('../modules/operational_dashboard/components/RouteAnalysis/RouteMapVisualization', () => ({
  RouteMapVisualization: ({ synthesisResult }: any) => (
    <div data-testid="route-map-visualization">
      Map Visualization for: {synthesisResult?.site_name}
    </div>
  ),
}));

const mockPlants = [
  { plant_id: 'p1', plant_code: 'ACC_VASCO', plant_name: 'Vasco Plant', latitude: 15.3991, longitude: 73.8153, is_active: true, location_type: 'PLANT' },
  { plant_id: 'p2', plant_code: 'ACC_KUNDAIM', plant_name: 'Kundaim Plant', latitude: 15.4215, longitude: 73.9856, is_active: true, location_type: 'PLANT' },
  { plant_id: 'p3', plant_code: 'ACC_DHARGA', plant_name: 'Dharga Plant', latitude: 15.6025, longitude: 73.8201, is_active: true, location_type: 'PLANT' },
  { plant_id: 'p4', plant_code: 'ACC_NESSAI', plant_name: 'Nessai Plant', latitude: 15.2635, longitude: 74.0152, is_active: true, location_type: 'PLANT' },
];

const mockResult = {
  analysis_id: 'test-analysis-uuid',
  analysis_context: 'TM_INCIDENT_ACCESS',
  incident_type: 'TM_STUCK_IN_TRAFFIC',
  reported_latitude: 15.4989,
  reported_longitude: 73.8278,
  reported_location_name: 'Panaji Mandovi Bridge',
  reported_timestamp: null,
  analysis_timestamp: '2026-09-09T10:00:00Z',
  dispatch_reference: 'DSP-100',
  vehicle_reference: 'TM-01',
  operator_notes: 'Heavy rain traffic',
  operator_identity: 'admin_user',
  best_access_plant_id: 'p3',
  best_access_plant_code: 'ACC_DHARGA',
  best_access_plant_name: 'Dharga Plant',
  best_access_eta_minutes: 14.2,
  best_access_distance_km: 12.1,
  best_access_traffic_delay_minutes: 1.5,
  decision_state: 'BEST_CURRENT_ACCESS',
  decision_summary: 'ACC_DHARGA has the shortest current road ETA (14.2 mins) to operator-reported incident location.',
  operational_advisory: 'Operational Advisory Only: Live TM location and truck availability are not evaluated. Final dispatch decision remains with Operations.',
  historical_evidence_status: 'INSUFFICIENT_NO_INCIDENT_BASELINE',
  is_google_fresh: true,
  is_google_stale_cache: false,
  google_cache_age_seconds: 0.0,
  candidate_access_matrix: [
    {
      plant_id: 'p1',
      plant_code: 'ACC_VASCO',
      plant_name: 'Vasco Plant',
      plant_latitude: 15.3991,
      plant_longitude: 73.8153,
      incident_latitude: 15.4989,
      incident_longitude: 73.8278,
      crow_fly_distance_km: 11.2,
      road_distance_km: 16.2,
      duration_minutes: 18.5,
      static_duration_minutes: 16.4,
      traffic_delay_minutes: 2.1,
      route_status: 'OK',
      failure_reason: null,
      ranking: 2,
      is_best_access: false,
      google_queried_at: '2026-09-09T10:00:00Z',
      provider_response_at: '2026-09-09T10:00:00Z',
      cache_age_seconds: 0.0,
      is_cached_result: false,
      is_stale: false,
      detailed_route: null,
    },
    {
      plant_id: 'p3',
      plant_code: 'ACC_DHARGA',
      plant_name: 'Dharga Plant',
      plant_latitude: 15.6025,
      plant_longitude: 73.8201,
      incident_latitude: 15.4989,
      incident_longitude: 73.8278,
      crow_fly_distance_km: 12.0,
      road_distance_km: 12.1,
      duration_minutes: 14.2,
      static_duration_minutes: 12.7,
      traffic_delay_minutes: 1.5,
      route_status: 'OK',
      failure_reason: null,
      ranking: 1,
      is_best_access: true,
      google_queried_at: '2026-09-09T10:00:00Z',
      provider_response_at: '2026-09-09T10:00:00Z',
      cache_age_seconds: 0.0,
      is_cached_result: false,
      is_stale: false,
      detailed_route: null,
    },
    {
      plant_id: 'p2',
      plant_code: 'ACC_KUNDAIM',
      plant_name: 'Kundaim Plant',
      plant_latitude: 15.4215,
      plant_longitude: 73.9856,
      incident_latitude: 15.4989,
      incident_longitude: 73.8278,
      crow_fly_distance_km: 19.5,
      road_distance_km: 26.8,
      duration_minutes: 36.2,
      static_duration_minutes: 28.0,
      traffic_delay_minutes: 8.2,
      route_status: 'OK',
      failure_reason: null,
      ranking: 3,
      is_best_access: false,
      google_queried_at: '2026-09-09T10:00:00Z',
      provider_response_at: '2026-09-09T10:00:00Z',
      cache_age_seconds: 0.0,
      is_cached_result: false,
      is_stale: false,
      detailed_route: null,
    },
  ],
  engine_version: 'v1.2.1',
  policy_version: 'INCIDENT_POLICY_v1.0.0',
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('WS-ROUT TM Incident / Stuck TM Current-Traffic Decision Support Frontend Workspace', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockImplementation((url: string, opts?: any) => {
      if (typeof url === 'string' && url.includes('plants')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ success: true, total_plants: 4, plants: mockPlants }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: true, data: mockResult }),
      });
    });
  });

  it('renders operator incident report input form and default Goa plants', async () => {
    render(<TMIncidentAccessWorkspace />, { wrapper: createWrapper() });

    expect(screen.getByText(/TM Incident \/ Stuck TM Current-Traffic Decision Support/i)).toBeInTheDocument();
    expect(screen.getByText(/Operator Incident Report Input/i)).toBeInTheDocument();
    expect(screen.getByText(/Decision Support Only/i)).toBeInTheDocument();
    expect(screen.getByTestId('btn-analyze-incident')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('ACC_VASCO')).toBeInTheDocument();
      expect(screen.getByText('ACC_KUNDAIM')).toBeInTheDocument();
    });
  });

  it('validates coordinates before sending analysis request', async () => {
    render(<TMIncidentAccessWorkspace />, { wrapper: createWrapper() });

    const latInput = screen.getByDisplayValue('15.4989');
    fireEvent.change(latInput, { target: { value: '120.0' } });

    const btn = screen.getByTestId('btn-analyze-incident');
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getByText(/Latitude must be between -90 and 90/i)).toBeInTheDocument();
    });
  });

  it('executes analysis and renders ranking table in strict ascending rank order (#1 BEST first)', async () => {
    render(<TMIncidentAccessWorkspace />, { wrapper: createWrapper() });

    const btn = screen.getByTestId('btn-analyze-incident');
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getByText(/Fastest Access Plant/i)).toBeInTheDocument();
    });

    expect(screen.getAllByText(/14.2/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/#1 BEST/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Operational Advisory Only:/i).length).toBeGreaterThan(0);
    expect(screen.getByTestId('route-map-visualization')).toBeInTheDocument();

    // Verify row ordering in DOM: rank 1 (ACC_DHARGA) should appear before rank 2 (ACC_VASCO)
    const table = screen.getByRole('table');
    const rows = table.querySelectorAll('tbody tr');
    expect(rows.length).toBe(3);
    expect(rows[0].textContent).toContain('#1 BEST');
    expect(rows[0].textContent).toContain('ACC_DHARGA');
    expect(rows[1].textContent).toContain('#2');
    expect(rows[1].textContent).toContain('ACC_VASCO');
    expect(rows[2].textContent).toContain('#3');
    expect(rows[2].textContent).toContain('ACC_KUNDAIM');
  });
});
