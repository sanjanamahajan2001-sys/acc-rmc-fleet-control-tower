import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReportExecutionHistoryTable } from '../components/ReportExecutionHistoryTable';

import { downloadReportArtifact } from '../utils/downloadReportArtifact';
import { ReportExecutionResponse, ReportStatus, ScopeValidationStatus, ReportFormat } from '../types/report.types';

vi.mock('../utils/downloadReportArtifact', () => ({
  downloadReportArtifact: vi.fn(),
}));

describe('WS6.2 - Report Execution History Table Suite', () => {
  const mockExecutions: ReportExecutionResponse[] = [
    {
      execution_id: 'REPLOG-COMPLETED-100',
      report_id: 'site_operations',
      report_type: 'site',
      format: ReportFormat.PDF,
      requested_by: 'user_alpha',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: { plant_id: 'VASCO' },
      effective_scope: { plant_id: 'VASCO' },
      scope_fingerprint: 'fp-100',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 42,
      status: ReportStatus.COMPLETED,
    },
    {
      execution_id: 'REPLOG-FAILED-200',
      report_id: 'fleet_operations',
      report_type: 'fleet',
      format: ReportFormat.XLSX,
      requested_by: 'user_beta',
      requested_at: '2026-08-20T12:05:00Z',
      requested_scope: { plant_id: 'NESSAI' },
      effective_scope: { plant_id: 'NESSAI' },
      scope_fingerprint: 'fp-200',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 0,
      status: ReportStatus.FAILED,
      error_message: 'Timeout Error',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. renders execution history rows with status chips and IDs', () => {
    render(<ReportExecutionHistoryTable executions={mockExecutions} />);

    expect(screen.getByText('REPLOG-COMPLETED-100')).toBeInTheDocument();
    expect(screen.getByText('REPLOG-FAILED-200')).toBeInTheDocument();
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    expect(screen.getByText('FAILED')).toBeInTheDocument();
  });

  it('2. opens scope modal when Scope button is clicked', async () => {
    render(<ReportExecutionHistoryTable executions={mockExecutions} />);

    const scopeBtn = screen.getByTestId('scope-btn-REPLOG-COMPLETED-100');
    fireEvent.click(scopeBtn);

    await waitFor(() => {
      expect(screen.getByTestId('execution-scope-modal')).toBeInTheDocument();
      expect(screen.getByText('Immutable Execution Scope Details')).toBeInTheDocument();
      expect(screen.getByText('fp-100')).toBeInTheDocument();
    });
  });

  it('3. enables download button ONLY for COMPLETED executions and triggers downloader', async () => {
    render(<ReportExecutionHistoryTable executions={mockExecutions} />);

    // Download button exists for COMPLETED execution
    const downloadBtn = screen.getByTestId('download-btn-REPLOG-COMPLETED-100');
    expect(downloadBtn).toBeInTheDocument();

    // Download button does NOT exist for FAILED execution
    expect(screen.queryByTestId('download-btn-REPLOG-FAILED-200')).not.toBeInTheDocument();

    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(downloadReportArtifact).toHaveBeenCalledWith({
        executionId: 'REPLOG-COMPLETED-100',
        format: ReportFormat.PDF,
        reportId: 'site_operations',
      });
    });
  });

  it('4. displays empty history state when zero execution records exist', () => {
    render(<ReportExecutionHistoryTable executions={[]} />);
    expect(screen.getByTestId('history-empty-state')).toBeInTheDocument();
    expect(screen.getByText('No historical report executions found.')).toBeInTheDocument();
  });
});
