import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { TimelineReplayDashboardPage } from '../pages/TimelineReplayDashboardPage';
import { TimelineSpatialContextPanel } from '../components/TimelineSpatialContextPanel';
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

const mockDispatchDetail: apiModule.DispatchTimelineReplayDetail = {
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
  ],
  telemetry_summary: {
    avg_speed_kmh: 35.5,
    max_speed_kmh: 62.0,
    drum_rotation_rpm: 3.5,
    telemetry_matched: true,
  },
  spatial_context: {
    has_gps_breadcrumbs: false,
    spatial_mode: 'NO_SPATIAL_DATA',
    plant_latitude: null,
    plant_longitude: null,
    site_latitude: null,
    site_longitude: null,
    trajectory_points: [],
  },
  correlated_alert_count: 1,
};

describe('WS-08.7 Dedicated UX & Evidence Enhancements Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // TEST 1 — Queue renders TELEMETRY MATCHED when authoritative telemetry flag exists
  it('TEST 1: Queue renders TELEMETRY MATCHED badge when item.has_telemetry is true', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText('TELEMETRY').length).toBeGreaterThan(0);
    });
  });

  // TEST 2 — Queue renders NO LOCATION when authoritative spatial mode is NO_SPATIAL_DATA
  it('TEST 2: Renders NO SPATIAL DATA badge cleanly in spatial panel for dispatches without coordinates', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText('NO SPATIAL DATA AVAILABLE').length).toBeGreaterThan(0);
    });
  });

  // TEST 3 — Telemetry availability is NOT incorrectly converted into spatial availability
  it('TEST 3: Telemetry matched flag does not create fake spatial trajectory points', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.queryByText(/GPS TRAJECTORY AVAILABLE/i)).toBeNull();
    });
  });

  // TEST 4 — Spatial panel renders PLANT LOCATION terminology
  it('TEST 4: Spatial panel component renders Plant Location terminology instead of Geofence Marker', () => {
    render(
      <TimelineSpatialContextPanel
        spatialContext={{
          has_gps_breadcrumbs: false,
          spatial_mode: 'LOCATION_CONTEXT_ONLY',
          plant_latitude: 15.452,
          plant_longitude: 73.918,
          site_latitude: 15.498,
          site_longitude: 73.827,
          trajectory_points: [],
        }}
        plantName="ACC DHARGA"
        customerName="A K MEHTA"
      />
    );

    expect(screen.getByText('Plant Location')).toBeInTheDocument();
    expect(screen.queryByText(/Plant Geofence Marker/i)).toBeNull();
  });

  // TEST 5 — Spatial panel renders SITE / UNLOADING LOCATION terminology
  it('TEST 5: Spatial panel component renders Site / Unloading Location terminology', () => {
    render(
      <TimelineSpatialContextPanel
        spatialContext={{
          has_gps_breadcrumbs: false,
          spatial_mode: 'LOCATION_CONTEXT_ONLY',
          plant_latitude: 15.452,
          plant_longitude: 73.918,
          site_latitude: 15.498,
          site_longitude: 73.827,
          trajectory_points: [],
        }}
        plantName="ACC DHARGA"
        customerName="A K MEHTA"
      />
    );

    expect(screen.getByText('Site / Unloading Location')).toBeInTheDocument();
  });

  // TEST 6 — LOCATION CONTEXT LINE is explicitly labelled NOT VEHICLE ROUTE
  it('TEST 6: Location Context Line legend explicitly warns (Not Vehicle Route)', () => {
    render(
      <TimelineSpatialContextPanel
        spatialContext={{
          has_gps_breadcrumbs: false,
          spatial_mode: 'LOCATION_CONTEXT_ONLY',
          plant_latitude: 15.452,
          plant_longitude: 73.918,
          site_latitude: 15.498,
          site_longitude: 73.827,
          trajectory_points: [],
        }}
        plantName="ACC DHARGA"
        customerName="A K MEHTA"
      />
    );

    expect(screen.getByText('Location Context Line')).toBeInTheDocument();
    expect(screen.getByText('(Not Vehicle Route)')).toBeInTheDocument();
  });

  // TEST 7 — Unsupported GEOFENCE terminology is absent from spatial presentation
  it('TEST 7: False Geofence terminology is strictly absent from spatial context panel', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Geofence Marker/i)).toBeNull();
    });
  });

  // TEST 8 — Selection changes do not leave stale evidence from previous dispatch
  it('TEST 8: Clearing selection cleanly removes dispatch evidence summary', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Clear')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Clear'));

    await waitFor(() => {
      expect(screen.getByText('No Dispatch Selected for Replay Investigation')).toBeInTheDocument();
    });
  });

  // TEST 9 — Existing playback controls continue working
  it('TEST 9: Playback controls toolbar functions cleanly', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Play Timeline/i })).toBeInTheDocument();
    });
  });

  // TEST 10 — Duration breakdown remains intact
  it('TEST 10: Trip duration breakdown remains persistent', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Trip Duration Breakdown')).toBeInTheDocument();
    });
  });
});
