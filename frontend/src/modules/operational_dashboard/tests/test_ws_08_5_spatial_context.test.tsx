import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { TimelineReplayDashboardPage } from '../pages/TimelineReplayDashboardPage';
import * as apiModule from '../api/timelineReplayApi';

// Mock Dashboard Filter & Sync Contexts
vi.mock('../../site_dashboard/orchestration/DashboardFilterProvider', () => ({
  DashboardFilterProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useDashboardFilters: () => ({
    filters: { plant_id: 'ACC_DHARGA', customer_id: 'CUST_A_K_MEHTA', dataset_type: 'REAL_ONLY' },
    plantOptions: [
      { id: 'ALL', name: 'All Plants' },
      { id: 'ACC_DHARGA', name: 'ACC DHARGA' },
    ],
    customerOptions: [
      { id: 'ALL', name: 'All Customers' },
      { id: 'CUST_A_K_MEHTA', name: 'A K MEHTA' },
    ],
    metadata: { operational_date: '2026-08-05', total_dispatches: 3532, dataset_id: 'DS-20260805-001' },
    setPlantFilter: vi.fn(),
    setCustomerFilter: vi.fn(),
    setDatasetTypeFilter: vi.fn(),
  }),
}));

vi.mock('../../site_dashboard/orchestration/DashboardSyncProvider', () => ({
  DashboardSyncProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useDashboardSync: () => ({
    syncStatus: { isSyncing: false, lastSyncedAt: new Date() },
  }),
}));

const mockDispatchList: apiModule.DispatchReplayListResponse = {
  items: [
    {
      dispatch_id: 'disp-101',
      dispatch_number: 'DISP-TCK-101',
      plant_id: '738e7712-d92d-43b0-9e28-2e9cc031f23b',
      customer_id: 'a1809613-44e8-4d5e-8d91-3cfcb901852f',
      vehicle_id: '207db1e8-5365-4612-b4e3-1fa1bef86d7f',
      dispatch_date: '2025-08-14T00:00:00Z',
      status: 'COMPLETED',
      has_telemetry: true,
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 50,
};

const createMockDetail = (spatialOverride: Partial<apiModule.SpatialContext>): apiModule.DispatchTimelineReplayDetail => ({
  dispatch_id: 'disp-101',
  dispatch_number: 'DISP-TCK-101',
  plant_id: '738e7712-d92d-43b0-9e28-2e9cc031f23b',
  customer_id: 'a1809613-44e8-4d5e-8d91-3cfcb901852f',
  vehicle_id: '207db1e8-5365-4612-b4e3-1fa1bef86d7f',
  dataset_id: null,
  status: 'COMPLETED',
  duration_summary: {
    total_trip_duration_mins: 85.0,
    duration_completeness: 'COMPLETE',
    missing_segments: [],
  },
  t2c_retention_mins: 5.0,
  lifecycle_events: [
    {
      event_type: 'Batched',
      authority_type: 'DIRECT',
      timestamp: '2025-08-14T08:00:00Z',
      duration_mins: 0,
      location_name: 'ACC DHARGA',
      is_inferred_estimate: false,
      notes: null,
    },
    {
      event_type: 'Returned',
      authority_type: 'DIRECT',
      timestamp: '2025-08-14T09:40:00Z',
      duration_mins: 20.0,
      location_name: 'ACC DHARGA',
      is_inferred_estimate: false,
      notes: null,
    },
  ],
  telemetry_summary: {
    avg_speed_kmh: 35.5,
    max_speed_kmh: 62.0,
    drum_rotation_rpm: 3.5,
    telemetry_matched: true,
  },
  spatial_context: {
    has_gps_breadcrumbs: false,
    spatial_mode: 'LOCATION_CONTEXT_ONLY',
    plant_latitude: 15.3981,
    plant_longitude: 73.8122,
    site_latitude: 15.4989,
    site_longitude: 73.8278,
    trajectory_points: [],
    ...spatialOverride,
  },
  correlated_alert_count: 1,
});

describe('WS-08.5 Dedicated Spatial Context Test Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // TEST 1 — GPS_TRAJECTORY renders actual trajectory points
  it('TEST 1: GPS_TRAJECTORY renders actual trajectory points when present', async () => {
    const detail = createMockDetail({
      spatial_mode: 'GPS_TRAJECTORY',
      has_gps_breadcrumbs: true,
      trajectory_points: [
        { latitude: 15.3981, longitude: 73.8122, timestamp: '2025-08-14T08:15:00Z', speed_kmh: 40, heading_deg: 180 },
        { latitude: 15.4500, longitude: 73.8200, timestamp: '2025-08-14T08:30:00Z', speed_kmh: 45, heading_deg: 180 },
      ],
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/GPS TRAJECTORY AVAILABLE \(2 BREADCRUMBS\)/i)).toBeInTheDocument();
      expect(screen.getByText(/GPS Trajectory Path \(2 pts\)/i)).toBeInTheDocument();
    });
  });

  // TEST 2 — GPS_TRAJECTORY with empty trajectory renders location fallback without fabricating points
  it('TEST 2: GPS_TRAJECTORY with empty trajectory renders location fallback without fabricating points', async () => {
    const detail = createMockDetail({
      spatial_mode: 'GPS_TRAJECTORY',
      has_gps_breadcrumbs: true,
      trajectory_points: [],
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/AUTHORITATIVE TIMELINE \(LOCATION CONTEXT ONLY - NO GPS BREADCRUMBS\)/i)).toBeInTheDocument();
    });
  });

  // TEST 3 — GPS_TRAJECTORY with has_gps_breadcrumbs=false does not render GPS trajectory
  it('TEST 3: GPS_TRAJECTORY with has_gps_breadcrumbs=false does not render GPS trajectory', async () => {
    const detail = createMockDetail({
      spatial_mode: 'GPS_TRAJECTORY',
      has_gps_breadcrumbs: false,
      trajectory_points: [{ latitude: 15.3981, longitude: 73.8122, timestamp: null, speed_kmh: null, heading_deg: null }],
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/AUTHORITATIVE TIMELINE \(LOCATION CONTEXT ONLY - NO GPS BREADCRUMBS\)/i)).toBeInTheDocument();
    });
  });

  // TEST 4 & 5 — LOCATION_CONTEXT_ONLY renders Plant/Site and explicit warning badge
  it('TEST 4 & 5: LOCATION_CONTEXT_ONLY renders Plant/Site coordinates and explicit warning badge', async () => {
    const detail = createMockDetail({
      spatial_mode: 'LOCATION_CONTEXT_ONLY',
      has_gps_breadcrumbs: false,
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/AUTHORITATIVE TIMELINE \(LOCATION CONTEXT ONLY - NO GPS BREADCRUMBS\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Lat: 15.398100, Lon: 73.812200/i)).toBeInTheDocument();
      expect(screen.getByText(/Lat: 15.498900, Lon: 73.827800/i)).toBeInTheDocument();
    });
  });

  // TEST 6 — LOCATION_CONTEXT_ONLY connection is labeled as location context line, not vehicle route
  it('TEST 6: LOCATION_CONTEXT_ONLY connection is labeled as location context line', async () => {
    const detail = createMockDetail({
      spatial_mode: 'LOCATION_CONTEXT_ONLY',
      has_gps_breadcrumbs: false,
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Location Context Line')).toBeInTheDocument();
      expect(screen.queryByText('Vehicle Route')).toBeNull();
      expect(screen.queryByText('GPS Route')).toBeNull();
    });
  });

  // TEST 7 — NO_SPATIAL_DATA renders clean fallback
  it('TEST 7: NO_SPATIAL_DATA renders clean fallback card', async () => {
    const detail = createMockDetail({
      spatial_mode: 'NO_SPATIAL_DATA',
      plant_latitude: null,
      plant_longitude: null,
      site_latitude: null,
      site_longitude: null,
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText('NO SPATIAL DATA AVAILABLE').length).toBeGreaterThan(0);
    });
  });

  // TEST 8 & 9 — Missing Plant or Site coordinates handled safely
  it('TEST 8 & 9: Safe handling when plant or site coordinates are missing', async () => {
    const detail = createMockDetail({
      spatial_mode: 'LOCATION_CONTEXT_ONLY',
      plant_latitude: 15.3981,
      plant_longitude: 73.8122,
      site_latitude: null,
      site_longitude: null,
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Lat: 15.398100, Lon: 73.812200/i)).toBeInTheDocument();
      expect(screen.getByText('Coordinates Unavailable')).toBeInTheDocument();
    });
  });

  // TEST 10 — Both coordinate sets missing do not generate fake coordinates
  it('TEST 10: Missing both coordinates does not generate fake 0,0 coordinates', async () => {
    const detail = createMockDetail({
      spatial_mode: 'LOCATION_CONTEXT_ONLY',
      plant_latitude: null,
      plant_longitude: null,
      site_latitude: null,
      site_longitude: null,
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Lat: 0.000000/i)).toBeNull();
      expect(screen.getAllByText('NO SPATIAL DATA AVAILABLE').length).toBeGreaterThan(0);
    });
  });

  // TEST 11 — Friendly Plant/Customer names remain visible
  it('TEST 11: Displays friendly plant and customer names in spatial labels', async () => {
    const detail = createMockDetail({
      spatial_mode: 'LOCATION_CONTEXT_ONLY',
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/ACC DHARGA/i)).toBeInTheDocument();
      expect(screen.getByText(/A K MEHTA/i)).toBeInTheDocument();
    });
  });

  // TEST 12 & 13 — Switching selected dispatch updates spatial context without stale state
  it('TEST 12 & 13: Switching selected dispatch updates spatial context without retaining stale state', async () => {
    const detail1 = createMockDetail({
      spatial_mode: 'GPS_TRAJECTORY',
      has_gps_breadcrumbs: true,
      trajectory_points: [{ latitude: 15.3981, longitude: 73.8122, timestamp: null, speed_kmh: null, heading_deg: null }],
    });

    const detail2 = createMockDetail({
      spatial_mode: 'NO_SPATIAL_DATA',
      has_gps_breadcrumbs: false,
      plant_latitude: null,
      plant_longitude: null,
      site_latitude: null,
      site_longitude: null,
      trajectory_points: [],
    });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue({
      items: [
        { ...mockDispatchList.items[0], dispatch_id: 'disp-1', dispatch_number: 'DISP-1' },
        { ...mockDispatchList.items[0], dispatch_id: 'disp-2', dispatch_number: 'DISP-2' },
      ],
      total_count: 2,
      page: 1,
      page_size: 50,
    });

    const detailSpy = vi.spyOn(apiModule, 'fetchDispatchTimelineDetail');
    detailSpy.mockResolvedValueOnce(detail1).mockResolvedValueOnce(detail2);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/GPS TRAJECTORY AVAILABLE/i)).toBeInTheDocument();
    });

    const dispButtons = screen.getAllByText('DISP-2');
    fireEvent.click(dispButtons[0]);

    await waitFor(() => {
      expect(screen.getAllByText('NO SPATIAL DATA AVAILABLE').length).toBeGreaterThan(0);
      expect(screen.queryByText(/GPS TRAJECTORY AVAILABLE/i)).toBeNull();
    });
  });

  // TEST 14 — No external GIS dependency introduced
  it('TEST 14: Renders pure inline SVG spatial visualization without external GIS scripts', async () => {
    const detail = createMockDetail({ spatial_mode: 'LOCATION_CONTEXT_ONLY' });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    const { container } = render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });

  // TEST 15 — Component does not modify replay state
  it('TEST 15: Spatial component mounting does not modify replay controls or step state', async () => {
    const detail = createMockDetail({ spatial_mode: 'LOCATION_CONTEXT_ONLY' });

    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(detail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Play Timeline/i })).toBeInTheDocument();
      expect(screen.getByText(/Replay Journey Investigation Controls/i)).toBeInTheDocument();
    });
  });
});
