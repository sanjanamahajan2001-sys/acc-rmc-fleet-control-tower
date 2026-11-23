import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { ReportsManagementPage } from '../pages/ReportsManagementPage';
import { useReportsStore } from '../store/reports.store';
import { reportsApiClient } from '../api/reports.api';
import { ReportFormat, ReportDefinitionDTO } from '../types/report.types';
import { DashboardFilterProvider } from '../../site_dashboard/orchestration/DashboardFilterProvider';

vi.mock('../api/reports.api', () => ({
  reportsApiClient: {
    listReports: vi.fn(),
    generateReportAsync: vi.fn(),
    getExecutionStatus: vi.fn(),
  },
}));

describe('WS6.1 - Reports Management Workspace & Catalog Suite', () => {
  const mockCatalog: ReportDefinitionDTO[] = [
    {
      report_id: 'site_operations',
      title: 'Site Operations Dashboard',
      description: 'Site ops performance',
      source_service: 'site_dashboard',
      supported_formats: [ReportFormat.PDF, ReportFormat.XLSX],
      category: 'OPERATIONAL',
      permission_role: 'VIEWER',
      is_active: true,
    },
    {
      report_id: 'fleet_operations',
      title: 'Fleet Operations Dashboard',
      description: 'Fleet metrics',
      source_service: 'fleet_dashboard',
      supported_formats: [ReportFormat.PDF],
      category: 'FLEET',
      permission_role: 'VIEWER',
      is_active: false,
    },
  ];

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

  const renderComponent = () =>
    render(
      <MemoryRouter>
        <DashboardFilterProvider>
          <ReportsManagementPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

  it('1. loads catalog on mount and renders report catalog cards', async () => {
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockCatalog);

    renderComponent();

    expect(reportsApiClient.listReports).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText('Site Operations Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Fleet Operations Dashboard')).toBeInTheDocument();
    });
  });

  it('2. filters catalog grid based on search query', async () => {
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockResolvedValue(mockCatalog);
    useReportsStore.setState({ catalog: mockCatalog, isCatalogLoading: false });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Site Operations Dashboard')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('catalog-search-input');
    fireEvent.change(searchInput, { target: { value: 'Site' } });

    expect(screen.getByText('Site Operations Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Fleet Operations Dashboard')).not.toBeInTheDocument();
  });

  it('3. opens ReportExportModal when Export button is clicked', async () => {
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockResolvedValue(mockCatalog);
    useReportsStore.setState({ catalog: mockCatalog, isCatalogLoading: false });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('export-btn-site_operations')).toBeInTheDocument();
    });

    const exportBtn = screen.getByTestId('export-btn-site_operations');
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByText('Export Report — Site Operations Dashboard')).toBeInTheDocument();
    });
  });

  it('4. disables export action for inactive report definition', async () => {
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockResolvedValue(mockCatalog);
    useReportsStore.setState({ catalog: mockCatalog, isCatalogLoading: false });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('export-btn-fleet_operations')).toBeInTheDocument();
    });

    const disabledBtn = screen.getByTestId('export-btn-fleet_operations');
    expect(disabledBtn).toBeDisabled();
  });


  it('5. displays error banner on catalog fetch failure and allows retry', async () => {
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('Catalog Network Failure')
    );

    renderComponent();

    await waitFor(() => {
      expect(screen.getByTestId('catalog-error-banner')).toBeInTheDocument();
    });

    expect(screen.getByText('Catalog Network Failure')).toBeInTheDocument();
  });
});
