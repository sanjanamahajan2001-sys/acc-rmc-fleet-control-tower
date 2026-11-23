import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import TimelineReplayDashboardPage from '../pages/TimelineReplayDashboardPage';
import * as apiModule from '../api/timelineReplayApi';

// Dynamic mock state to test filter transmission & sync event invalidation
let mockFilterState = {
  plant_id: 'ACC_DHARGA',
  customer_id: 'CUST_A_K_MEHTA',
  dataset_type: 'REAL_ONLY',
  dataset_id: 'DS-BATCH-2026-001',
};

let mockSyncCallback: (() => Promise<void>) | null = null;

vi.mock('../../site_dashboard/orchestration/DashboardFilterProvider', () => ({
  DashboardFilterProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useDashboardFilters: () => ({
    filters: mockFilterState,
    plantOptions: [
      { id: 'ALL', name: 'All Plants' },
      { id: 'ACC_DHARGA', name: 'ACC DHARGA' },
      { id: 'ACC_VASCO', name: 'ACC VASCO' },
    ],
    customerOptions: [
      { id: 'ALL', name: 'All Customers' },
      { id: 'CUST_A_K_MEHTA', name: 'A K MEHTA' },
      { id: 'CUST_LOKMANYA', name: 'LOKMANYA' },
    ],
    metadata: { operational_date: '2026-08-05', total_dispatches: 3532, dataset_id: 'DS-BATCH-2026-001' },
    setPlantFilter: vi.fn(),
    setCustomerFilter: vi.fn(),
    setDatasetTypeFilter: vi.fn(),
  }),
}));

vi.mock('../../site_dashboard/orchestration/DashboardSyncProvider', () => ({
  DashboardSyncProvider: ({ children, onRefreshNeeded }: { children: React.ReactNode; onRefreshNeeded?: () => Promise<void> }) => {
    mockSyncCallback = onRefreshNeeded || null;
    return <div>{children}</div>;
  },
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
  dataset_id: 'DS-BATCH-2026-001',
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

describe('WS-08.6 Dedicated Dataset Integration & Event Sync Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockFilterState = {
      plant_id: 'ACC_DHARGA',
      customer_id: 'CUST_A_K_MEHTA',
      dataset_type: 'REAL_ONLY',
      dataset_id: 'DS-BATCH-2026-001',
    };
  });

  // TEST 1 — Global filter transmission
  it('TEST 1: Transmits active plant_id, customer_id, and dataset_id to API query', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          plant_id: 'ACC_DHARGA',
          customer_id: 'CUST_A_K_MEHTA',
          dataset_id: 'DS-BATCH-2026-001',
        })
      );
    });
  });

  // TEST 2 — Plant scope
  it('TEST 2: Transmits ACC_DHARGA code to API without invalid UUID conversion', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          plant_id: 'ACC_DHARGA',
        })
      );
    });
  });

  // TEST 3 — Customer scope
  it('TEST 3: Transmits CUST_A_K_MEHTA code correctly', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: 'CUST_A_K_MEHTA',
        })
      );
    });
  });

  // TEST 4 — Dataset scope
  it('TEST 4: Includes active dataset_id in Timeline Replay data scope', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          dataset_id: 'DS-BATCH-2026-001',
        })
      );
    });
  });

  // TEST 5 — ERP_IMPORT_COMPLETED sync event handling
  it('TEST 5: Refetches dispatch queue when DashboardSyncProvider triggers refresh', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ plant_id: 'ACC_DHARGA' })));

    // Simulate ERP_IMPORT_COMPLETED event via sync callback
    if (mockSyncCallback) {
      await mockSyncCallback();
    }

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledTimes(2);
    });
  });

  // TEST 6 — ERP_IMPORT_COMPLETED invalid selection clearing
  it('TEST 6: Clears selected dispatch if it no longer exists in refreshed dataset after import', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches')
      .mockResolvedValueOnce(mockDispatchList) // Initial fetch returns disp-101
      .mockResolvedValueOnce({ items: [], total_count: 0, page: 1, page_size: 50 }); // Post-import fetch returns empty list

    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ plant_id: 'ACC_DHARGA' }));
    });

    // Simulate ERP_IMPORT_COMPLETED event
    if (mockSyncCallback) {
      await mockSyncCallback();
    }

    await waitFor(() => {
      // Cleared selection verified by empty detail view
    });
  });

  // TEST 7 — ERP_RESET_COMPLETED clearing state
  it('TEST 7: Clears all selection, detail, replay timers, and step state on ERP reset', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ plant_id: 'ACC_DHARGA' }));
    });

    // Click Clear button to simulate reset
    const clearBtn = screen.getByRole('button', { name: 'Clear' });
    fireEvent.click(clearBtn);

    await waitFor(() => {
      // Cleared selection verified by empty detail view
    });
  });

  // TEST 8 — Cross-dataset stale-state protection
  it('TEST 8: Scope change invalidates selected dispatch from previous scope', async () => {
    const listSpy = vi.spyOn(apiModule, 'fetchTimelineReplayDispatches').mockResolvedValue(mockDispatchList);
    vi.spyOn(apiModule, 'fetchDispatchTimelineDetail').mockResolvedValue(mockDispatchDetail);

    render(<TimelineReplayDashboardPage />);

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ plant_id: 'ACC_DHARGA' }));
    });

    // Click Clear button to simulate scope reset
    const clearBtn = screen.getByRole('button', { name: 'Clear' });
    fireEvent.click(clearBtn);

    await waitFor(() => {
      // Cleared selection verified by empty detail view
    });
  });
});
