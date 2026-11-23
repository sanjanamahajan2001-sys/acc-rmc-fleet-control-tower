import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { Sidebar } from '../../../layouts/Sidebar';
import { ReportsManagementPage } from '../pages/ReportsManagementPage';
import { DashboardFilterProvider } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { useReportsStore } from '../store/reports.store';
import { reportsApiClient } from '../api/reports.api';

vi.mock('../api/reports.api', () => ({
  reportsApiClient: {
    listReports: vi.fn(),
    generateReportAsync: vi.fn(),
    getExecutionStatus: vi.fn(),
  },
}));

describe('WS6.3 - Router & Navigation Integration Suite', () => {
  beforeEach(() => {
    useReportsStore.setState({
      catalog: [],
      isCatalogLoading: false,
      catalogError: null,
      executions: {},
      pollingMap: {},
    });
    vi.clearAllMocks();
  });

  it('1. renders Reports & Exports link in Sidebar navigation', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <DashboardFilterProvider>
          <Sidebar />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    const reportsLink = screen.getByText('Reports & Exports');
    expect(reportsLink).toBeInTheDocument();
  });

  it('2. routes to /reports and renders ReportsManagementPage', async () => {
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      {
        report_id: 'site_operations',
        title: 'Site Operations Dashboard',
        description: 'Site ops',
        source_service: 'site',
        supported_formats: ['PDF'],
        category: 'OPERATIONAL',
        permission_role: 'VIEWER',
        is_active: true,
      },
    ]);

    render(
      <MemoryRouter initialEntries={['/reports']}>
        <DashboardFilterProvider>
          <Routes>
            <Route path="/reports" element={<ReportsManagementPage />} />
          </Routes>
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Authoritative Report Catalog')).toBeInTheDocument();
      expect(screen.getByText('Site Operations Dashboard')).toBeInTheDocument();
    });
  });

  it('3. highlights Reports & Exports active navigation link when on /reports', () => {
    render(
      <MemoryRouter initialEntries={['/reports']}>
        <DashboardFilterProvider>
          <Sidebar />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    const reportsLink = screen.getByText('Reports & Exports').closest('a');
    expect(reportsLink).toHaveClass('border-l-blue-700');
  });
});

