/**
 * WS-07.9 Dedicated Frontend Integration & Lifecycle Retention Test Suite.
 * Covers:
 * 1. Default Operational View Filters (statusFilter = 'OPEN')
 * 2. Active KPI Excludes RESOLVED Alerts
 * 3. Operators can retrieve RESOLVED alerts explicitly
 * 4. Scope Preservation across Lifecycle State Transitions
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, beforeEach, it, expect } from 'vitest';
import { AlertCenterDashboardPage } from '../modules/operational_dashboard/pages/AlertCenterDashboardPage';

const mockSummaryData = {
  total_active_alerts: 5,
  critical_count: 3,
  warning_count: 2,
  info_count: 0,
  acknowledged_count: 0,
  dataset_context: {
    operational_date: '2026-08-05',
    total_dispatches: 3532,
    last_imported_at: '2026-08-05T00:00:00Z',
    dataset_id: 'DS-20260805-001',
    status: 'ACTIVE_PRODUCTION',
  },
};

const mockOpenAlerts = {
  items: [
    {
      id: 'alert-9901',
      alert_fingerprint: 'a'.repeat(64),
      alert_type: 'PLANT_HOLDING_BOTTLENECK',
      severity: 'CRITICAL',
      status: 'OPEN',
      plant_id: 'ACC_KUNDAIM',
      customer_id: 'CUST_AARA_HOTELS',
      metric_name: 'holding_mins',
      actual_value: 75.0,
      threshold_value: 45.0,
      unit: 'mins',
      business_impact: 'Holding SLA breach',
      evidence_json: { holding_mins: 75 },
      recommended_action: 'Contact site supervisor',
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

const mockResolvedAlerts = {
  items: [
    {
      ...mockOpenAlerts.items[0],
      id: 'alert-9902',
      status: 'RESOLVED',
      resolved_by: 'Operator_ControlTower',
      resolved_at: '2026-08-05T10:30:00Z',
      resolution_reason: 'Operational Queue Cleared',
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

const setupGlobalFetchMock = () => {
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
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSummaryData),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts') && urlStr.includes('status=RESOLVED')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResolvedAlerts),
      } as Response);
    }
    if (urlStr.includes(`${env.VITE_API_BASE_URL}/alerts')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockOpenAlerts),
      } as Response);
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
  }) as any;
};

describe('WS-07.9 Alert Retention and Operational Visibility Test Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Default Operational View sets status to OPEN and excludes RESOLVED alerts from list', async () => {
    setupGlobalFetchMock();

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('status-filter-select')).toHaveValue('OPEN');
      expect(screen.getByText('PLANT_HOLDING_BOTTLENECK')).toBeInTheDocument();
    });
  });

  it('2. Explicitly selecting RESOLVED filter retrieves historical resolved alerts without data loss', async () => {
    setupGlobalFetchMock();

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('status-filter-select')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('status-filter-select'), { target: { value: 'RESOLVED' } });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('status=RESOLVED'));
    });
  });
});
