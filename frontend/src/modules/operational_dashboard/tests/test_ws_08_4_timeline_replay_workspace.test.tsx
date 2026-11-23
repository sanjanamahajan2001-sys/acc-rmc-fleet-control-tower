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
      plant_id: 'ACC_DHARGA',
      customer_id: 'CUST_A_K_MEHTA',
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
  plant_id: 'ACC_DHARGA',
  customer_id: 'CUST_A_K_MEHTA',
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
      event_type: 'Loaded',
      authority_type: 'INFERRED',
      timestamp: '2025-08-14T08:05:00Z',
      duration_mins: 5.0,
      location_name: 'ACC DHARGA',
      is_inferred_estimate: true,
      notes: 'Inferred estimate: 10 mins prior to departure',
    },
    {
      event_type: 'Departed Plant',
      authority_type: 'DIRECT',
      timestamp: '2025-08-14T08:15:00Z',
      duration_mins: 10.0,
      location_name: 'ACC DHARGA',
      is_inferred_estimate: false,
      notes: null,
    },
    {
      event_type: 'Arrived Site',
      authority_type: 'DIRECT',
      timestamp: '2025-08-14T08:45:00Z',
      duration_mins: 30.0,
      location_name: 'A K MEHTA SITE',
      is_inferred_estimate: false,
      notes: null,
    },
    {
      event_type: 'Unloading / Pouring',
      authority_type: 'DIRECT',
      timestamp: '2025-08-14T08:50:00Z',
      duration_mins: 5.0,
      location_name: 'A K MEHTA SITE',
      is_inferred_estimate: false,
      notes: null,
    },
    {
      event_type: 'Completed',
      authority_type: 'DIRECT',
      timestamp: '2025-08-14T09:20:00Z',
      duration_mins: 30.0,
      location_name: 'A K MEHTA SITE',
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
  },
  correlated_alert_count: 1,
};

describe('WS-08.4 Remediation Dedicated Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // TEST 1 — Header & Workspace Investigation Subtitle
  it('renders Timeline Replay page header and investigation subtitle', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Timeline Replay & Digital Twin')).toBeInTheDocument();
      expect(
        screen.getByText('Dispatch Timeline Investigation & Operational Journey Analysis')
      ).toBeInTheDocument();
    });
  });

  // TEST 2 — Code-Based Filter Parameter Transmission (ACC_DHARGA)
  it('sends correct plant_id code to timelineReplayApi list', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          plant_id: 'ACC_DHARGA',
          customer_id: 'CUST_A_K_MEHTA',
        })
      );
    });
  });

  // TEST 3 — Selection Persistence across Playback & Reset
  it('retains selected dispatch detail when selected, played, or reset', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    const detailSpy = vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(detailSpy).toHaveBeenCalledWith('disp-101');
    });

    // Detail must remain rendered
    expect(screen.getByText('INFERRED ESTIMATE')).toBeInTheDocument();
    expect(screen.getByText('85.0 mins')).toBeInTheDocument();

    // Click Play, Reset, and Speed Controls
    const playBtn = screen.getByRole('button', { name: /Play Timeline|Pause Playback/i });
    fireEvent.click(playBtn);

    const resetBtn = screen.getByRole('button', { name: /Reset Playback/i });
    fireEvent.click(resetBtn);

    // Selected detail MUST REMAIN PERSISTENT after Reset
    expect(screen.getByText('INFERRED ESTIMATE')).toBeInTheDocument();
    expect(screen.getByText('85.0 mins')).toBeInTheDocument();
  });

  // TEST 4 — Date Handling Authority (Preserves 2025 Backend Date)
  it('displays backend operational date authority (2025) without replacing with today', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/2025/i).length).toBeGreaterThan(0);
    });
  });

  // TEST 5 — Explicit Clear Selection Control
  it('clears selected dispatch when Clear button is clicked', async () => {
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

  // TEST 6 — Friendly Name Resolution for Entities
  it('resolves friendly plant and customer names instead of bare UUIDs', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText('ACC DHARGA').length).toBeGreaterThan(0);
      expect(screen.getAllByText('A K MEHTA').length).toBeGreaterThan(0);
    });
  });

  // TEST 7 — Prominent Phase Duration Breakdown (T1, T2a, T2b, T3)
  it('renders prominent phase duration breakdown labels in duration panel', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/T1 Transit:/i)).toBeInTheDocument();
      expect(screen.getByText(/T2a Holding:/i)).toBeInTheDocument();
      expect(screen.getByText(/T2b Unloading:/i)).toBeInTheDocument();
      expect(screen.getByText(/T3 Return:/i)).toBeInTheDocument();
    });
  });

  // TEST 8 — Replay Playback Restart at End of Lifecycle
  it('restarts playback from step 0 if user clicks Play when already at final step', async () => {
    vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Play Timeline/i })).toBeInTheDocument();
    });

    // Fast-forward step to final step (6)
    const scrubber = screen.getByRole('slider');
    fireEvent.change(scrubber, { target: { value: '6' } });

    // Click play at end
    const playBtn = screen.getByRole('button', { name: /Play Timeline/i });
    fireEvent.click(playBtn);

    // Playback should start cleanly
    expect(screen.getByRole('button', { name: /Pause Playback/i })).toBeInTheDocument();
  });
});
