import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReportExportModal } from '../components/ReportExportModal';

import { downloadReportArtifact } from '../utils/downloadReportArtifact';
import { reportsApiClient } from '../api/reports.api';
import { useReportsStore } from '../store/reports.store';
import { ReportFormat, ReportStatus, ScopeValidationStatus } from '../types/report.types';

vi.mock('../api/reports.api', () => ({
  reportsApiClient: {
    generateReportAsync: vi.fn(),
    getExecutionStatus: vi.fn(),
    getDownloadToken: vi.fn(),
    downloadArtifact: vi.fn(),
  },
}));

vi.mock('../utils/downloadReportArtifact', () => ({
  downloadReportArtifact: vi.fn(),
}));

describe('WS5.3 - Reusable Export Modal & Secure Download Suite', () => {
  beforeEach(() => {
    useReportsStore.setState({
      executions: {},
      pollingMap: {},
    });
    vi.clearAllMocks();
  });

  it('1. renders modal title and format selection when open', () => {
    render(
      <ReportExportModal
        isOpen={true}
        onClose={vi.fn()}
        reportId="site_operations"
        reportDefinition={{
          report_id: 'site_operations',
          title: 'Site Operations Dashboard',
          description: 'Desc',
          source_service: 'site',
          supported_formats: [ReportFormat.PDF, ReportFormat.XLSX],
          category: 'OPS',
          permission_role: 'VIEWER',
          is_active: true,
        }}
      />
    );

    expect(screen.getByText('Export Report — Site Operations Dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('export-modal-format-select')).toBeInTheDocument();
    expect(screen.getByTestId('export-modal-submit-button')).toBeInTheDocument();
  });

  it('2. submits async report request and triggers polling UX', async () => {
    const mockAsyncRes = {
      execution_id: 'REPLOG-MODAL-1',
      report_id: 'site_operations',
      report_type: 'site',
      format: ReportFormat.PDF,
      requested_by: 'SYSTEM',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 0,
      status: ReportStatus.QUEUED,
    };

    (reportsApiClient.generateReportAsync as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockAsyncRes);
    (reportsApiClient.getExecutionStatus as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockAsyncRes);

    render(
      <ReportExportModal
        isOpen={true}
        onClose={vi.fn()}
        reportId="site_operations"
        scope={{ plant_id: 'VASCO' }}
      />
    );

    const submitBtn = screen.getByTestId('export-modal-submit-button');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(reportsApiClient.generateReportAsync).toHaveBeenCalledWith({
        report_id: 'site_operations',
        format: ReportFormat.PDF,
        scope: { plant_id: 'VASCO' },
        requested_by: 'SYSTEM',
      });
    });

    expect(screen.getByTestId('export-modal-status-banner')).toBeInTheDocument();
  });

  it('3. displays download button on COMPLETED status and triggers download utility', async () => {
    const mockCompletedRes = {
      execution_id: 'REPLOG-COMPLETED-1',
      report_id: 'site_operations',
      report_type: 'site',
      format: ReportFormat.PDF,
      requested_by: 'SYSTEM',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 10,
      status: ReportStatus.COMPLETED,
    };

    (reportsApiClient.generateReportAsync as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockCompletedRes);
    (reportsApiClient.getExecutionStatus as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockCompletedRes);

    render(
      <ReportExportModal
        isOpen={true}
        onClose={vi.fn()}
        reportId="site_operations"
      />
    );

    fireEvent.click(screen.getByTestId('export-modal-submit-button'));

    await waitFor(() => {
      expect(screen.getByTestId('export-modal-download-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('export-modal-download-button'));

    await waitFor(() => {
      expect(downloadReportArtifact).toHaveBeenCalledWith(
        expect.objectContaining({
          executionId: 'REPLOG-COMPLETED-1',
          format: ReportFormat.PDF,
          reportId: 'site_operations',
        })
      );
    });
  });

  it('4. displays NO_DATA status without exposing download button', async () => {
    const mockNoDataRes = {
      execution_id: 'REPLOG-NODATA-1',
      report_id: 'alerts_incidents',
      report_type: 'alerts',
      format: ReportFormat.JSON,
      requested_by: 'SYSTEM',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 0,
      status: ReportStatus.NO_DATA,
    };

    (reportsApiClient.generateReportAsync as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockNoDataRes);
    (reportsApiClient.getExecutionStatus as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockNoDataRes);

    render(
      <ReportExportModal
        isOpen={true}
        onClose={vi.fn()}
        reportId="alerts_incidents"
      />
    );

    fireEvent.click(screen.getByTestId('export-modal-submit-button'));

    await waitFor(() => {
      expect(screen.getByText('Report generated with no matching data.')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('export-modal-download-button')).not.toBeInTheDocument();
  });
});
