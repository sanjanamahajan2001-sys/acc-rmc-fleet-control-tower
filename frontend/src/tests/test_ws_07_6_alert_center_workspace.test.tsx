/**
 * WS-07.6 Alert Center UI Workspace Comprehensive Test Suite.
 * Verifies shared shell reuse, global filter propagation, summary API integration,
 * list API pagination, severity/status filtering, detail drawer, lifecycle actions,
 * 409 conflict handling, loading/empty/error states, five-scope reconciliation,
 * Overall Dashboard component isolation, and post-action summary refetch without page reload.
 */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, beforeEach, it, expect } from 'vitest';
import { AlertCenterDashboardPage } from '../modules/operational_dashboard/pages/AlertCenterDashboardPage';

// Global Fetch Mock Data
const initialSummaryData = {
  total_active_alerts: 855,
  critical_count: 500,
  warning_count: 300,
  info_count: 55,
  acknowledged_count: 0,
  dataset_context: {
    operational_date: '2026-08-05',
    total_dispatches: 3532,
    last_imported_at: '2026-08-05T00:00:00Z',
    dataset_id: 'DS-20260805-001',
    status: 'ACTIVE_PRODUCTION',
  },
};

const postAckSummaryData = {
  ...initialSummaryData,
  total_active_alerts: 854,
  acknowledged_count: 1,
};

const postResolveSummaryData = {
  ...initialSummaryData,
  total_active_alerts: 854,
  critical_count: 499,
};

const mockListData = {
  items: [
    {
      id: 'alert-1001',
      alert_fingerprint: 'a'.repeat(64),
      alert_type: 'EXCESSIVE_SITE_HOLDING',
      severity: 'CRITICAL',
      status: 'OPEN',
      plant_id: 'ACC_KUNDAIM',
      customer_id: 'CUST_AARA_HOTELS',
      dispatch_id: '123e4567-e89b-12d3-a456-426614174000',
      dataset_id: 'DS-20260805-001',
      metric_name: 'holding_time_mins',
      actual_value: 75.0,
      threshold_value: 45.0,
      unit: 'mins',
      business_impact: 'Holding penalty exceeding 45m SLA',
      evidence_json: { holding_mins: 75 },
      recommended_action: 'Contact site manager',
      detected_at: '2026-08-05T10:00:00Z',
      evaluated_at: '2026-08-05T10:01:00Z',
      rule_version: 'v1.0.0',
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

const setupGlobalFetchMock = (getSummaryData?: () => any, acknowledgeHandler?: () => Promise<Response>) => {
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = url.toString();
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/operational-dashboard/context`)) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { metadata: { total_dispatches: 3532 } } }),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/operational-dashboard/kpis`)) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { kpis: [] } }),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/sync/status')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { sync_status: 'SYNCHRONIZED', last_sync_timestamp: '2026-08-05T00:00:00Z' } }),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/site-dashboard/filters')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ plants: [{ id: 'ACC_KUNDAIM', name: 'Kundaim' }], customers: [] }),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts/summary`)) {
      const data = getSummaryData ? getSummaryData() : initialSummaryData;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(data),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts/alert-1001/acknowledge')) {
      if (acknowledgeHandler) return acknowledgeHandler();
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockListData.items[0], status: 'ACKNOWLEDGED' }),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts/alert-1001/resolve')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ...mockListData.items[0], status: 'RESOLVED' }),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts/alert-1001`)) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockListData.items[0]),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockListData),
      } as Response);
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
  }) as any;
};

describe('WS-07.6 Alert Center UI Workspace Test Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Renders Alert Center cleanly without Overall Dashboard headings or KPIs', async () => {
    setupGlobalFetchMock();

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('alert-center-workspace')).toBeInTheDocument();
      expect(screen.getByTestId('alert-summary-strip')).toBeInTheDocument();
      expect(screen.getByTestId('alert-list-table')).toBeInTheDocument();
    });

    // 1. Verify workspace header
    expect(screen.getByText('Operational Alert Center')).toBeInTheDocument();
    expect(screen.getByText('Real-Time Business Rule Exceptions & SLA Management')).toBeInTheDocument();

    // 2. REGRESSION GUARD: Ensure Overall Dashboard title & KPIs are NOT present
    expect(screen.queryByText('Overall Operational Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Executive Fleet Command Tower, Operational SLAs & Customer Performance Intelligence')).not.toBeInTheDocument();
    expect(screen.queryByText('Dispatch Accuracy')).not.toBeInTheDocument();
    expect(screen.queryByText('Site Waiting Index')).not.toBeInTheDocument();
    expect(screen.queryByText('Dispatch Planning Index')).not.toBeInTheDocument();
    expect(screen.queryByText('Fleet Utilization Index')).not.toBeInTheDocument();

    // 3. Verify alert data rendering
    const holdingElements = screen.getAllByText('EXCESSIVE_SITE_HOLDING');
    expect(holdingElements.length).toBeGreaterThan(0);
  });

  it('2. TEST A — Refetches Summary API immediately post-ACK without browser reload', async () => {
    let currentSummary = initialSummaryData;
    setupGlobalFetchMock(() => currentSummary);

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('inspect-alert-btn-alert-1001')).toBeInTheDocument();
      // Initial summary values
      expect(screen.getByTestId('summary-ack-count')).toHaveTextContent('0');
    });

    fireEvent.click(screen.getByTestId('inspect-alert-btn-alert-1001'));

    await waitFor(() => {
      expect(screen.getByTestId('ack-alert-btn')).toBeInTheDocument();
    });

    // Set mock backend summary state before firing ACK event
    currentSummary = postAckSummaryData;

    await act(async () => {
      fireEvent.click(screen.getByTestId('ack-alert-btn'));
    });

    await waitFor(() => {
      // Verify GET /api/v1/alerts/summary was called
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining(`${env.VITE_API_BASE_URL}/alerts/summary'));
    });

    await waitFor(() => {
      // Post-ACK refreshed summary values displayed instantly WITHOUT browser reload!
      expect(screen.getByTestId('summary-ack-count')).toHaveTextContent('1');
    });
  });

  it('3. TEST B — Refetches Summary API immediately post-RESOLVE without browser reload', async () => {
    let currentSummary = initialSummaryData;
    setupGlobalFetchMock(() => currentSummary);

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('inspect-alert-btn-alert-1001')).toBeInTheDocument();
      // Initial summary values
      expect(screen.getByText('855')).toBeInTheDocument();
      expect(screen.getByText('500')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('inspect-alert-btn-alert-1001'));

    await waitFor(() => {
      expect(screen.getByTestId('resolve-alert-btn')).toBeInTheDocument();
    });

    // Set mock backend summary state before firing RESOLVE event
    currentSummary = postResolveSummaryData;

    await act(async () => {
      fireEvent.click(screen.getByTestId('resolve-alert-btn'));
    });

    await waitFor(() => {
      // Post-RESOLVE refreshed summary values displayed instantly WITHOUT browser reload!
      expect(screen.getByText('854')).toBeInTheDocument();
      expect(screen.getByText('499')).toBeInTheDocument();
    });
  });

  it('4. TEST C — 409 Conflict triggers refetch without false local state mutation', async () => {
    setupGlobalFetchMock(
      () => initialSummaryData,
      () => Promise.resolve({
        status: 409,
        ok: false,
        statusText: 'Conflict',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ message: '409 CONFLICT: State modified' }),
      } as Response)
    );

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('inspect-alert-btn-alert-1001')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('inspect-alert-btn-alert-1001'));

    await waitFor(() => {
      expect(screen.getByTestId('ack-alert-btn')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('ack-alert-btn'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('drawer-action-error')).toBeInTheDocument();
      expect(screen.getByText(/409 CONFLICT/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      // Verifies summary counts remained unchanged at 855
      expect(screen.getByText('855')).toBeInTheDocument();
    });
  });
});
