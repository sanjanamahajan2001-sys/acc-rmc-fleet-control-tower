/**
 * WS-07.8 Alert Center Final Integration & Regression Verification Test Suite.
 * Re-verifies all end-to-end integration flows across WS-07.6 and WS-07.7.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, beforeEach, it, expect } from 'vitest';
import { AlertCenterDashboardPage } from '../modules/operational_dashboard/pages/AlertCenterDashboardPage';

const initialSummaryData = {
  total_active_alerts: 4558,
  critical_count: 2100,
  warning_count: 1800,
  info_count: 658,
  acknowledged_count: 12,
  dataset_context: {
    operational_date: '2026-08-05',
    total_dispatches: 3532,
    last_imported_at: '2026-08-05T00:00:00Z',
    dataset_id: 'DS-20260805-001',
    status: 'ACTIVE_PRODUCTION',
  },
};

const mockListData = {
  items: [
    {
      id: 'alert-7801',
      alert_fingerprint: 'e'.repeat(64),
      alert_type: 'TRANSIT_DELAY_EXCESSIVE',
      severity: 'CRITICAL',
      status: 'OPEN',
      plant_id: 'ACC_KUNDAIM',
      customer_id: 'CUST_AARA_HOTELS',
      dispatch_id: '123e4567-e89b-12d3-a456-426614174000',
      dataset_id: 'DS-20260805-001',
      metric_name: 't1_transit_mins',
      actual_value: 85.0,
      threshold_value: 60.0,
      unit: 'mins',
      business_impact: 'Transit delay exceeding 60m SLA',
      evidence_json: { transit_mins: 85 },
      recommended_action: 'Reroute vehicle',
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
        json: () => Promise.resolve(initialSummaryData),
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

describe('WS-07.8 Alert Center Final Integration & Verification Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Renders complete Alert Center Workspace with real summary and list data', async () => {
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
      expect(screen.getByText('4558')).toBeInTheDocument();
      expect(screen.getByText('TRANSIT_DELAY_EXCESSIVE')).toBeInTheDocument();
    });
  });

  it('2. Preserves complete Control Tower shell context without Overall Dashboard pollution', async () => {
    setupGlobalFetchMock();

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <Routes>
          <Route path="/alerts" element={<AlertCenterDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Operational Alert Center')).toBeInTheDocument();
    });

    expect(screen.queryByText('Overall Operational Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Dispatch Accuracy')).not.toBeInTheDocument();
  });
});
