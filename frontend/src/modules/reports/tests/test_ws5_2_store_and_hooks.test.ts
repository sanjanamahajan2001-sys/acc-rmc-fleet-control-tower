import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useReportsStore } from '../store/reports.store';
import { useReportExecutionPoll, isTerminalStatus } from '../hooks/useReportExecutionPoll';
import { reportsApiClient } from '../api/reports.api';
import { ReportStatus, ScopeValidationStatus, ReportFormat } from '../types/report.types';

vi.mock('../api/reports.api', () => ({
  reportsApiClient: {
    listReports: vi.fn(),
    getExecutionStatus: vi.fn(),
  },
}));

describe('WS5.2 - Reports Zustand Store & Polling Hook Suite', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useReportsStore.setState({
      catalog: [],
      isCatalogLoading: false,
      catalogError: null,
      executions: {},
      pollingMap: {},
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('1. store initializes empty and loads catalog', async () => {
    const mockCatalog = [
      {
        report_id: 'site_operations',
        title: 'Site Operations',
        description: 'Site ops',
        source_service: 'site_dashboard',
        supported_formats: [ReportFormat.PDF],
        category: 'OPERATIONAL',
        permission_role: 'VIEWER',
        is_active: true,
      },
    ];
    (reportsApiClient.listReports as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockCatalog);

    const store = useReportsStore.getState();
    expect(store.catalog).toEqual([]);

    await act(async () => {
      await useReportsStore.getState().loadCatalog();
    });

    expect(useReportsStore.getState().catalog).toEqual(mockCatalog);
    expect(useReportsStore.getState().isCatalogLoading).toBe(false);
  });

  it('2. adds and updates executions by execution_id isolated', () => {
    const execA = {
      execution_id: 'REPLOG-A',
      report_id: 'site_operations',
      report_type: 'site',
      format: ReportFormat.PDF,
      requested_by: 'userA',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fpA',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 10,
      status: ReportStatus.QUEUED,
    };

    const execB = {
      execution_id: 'REPLOG-B',
      report_id: 'fleet_operations',
      report_type: 'fleet',
      format: ReportFormat.XLSX,
      requested_by: 'userB',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fpB',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 5,
      status: ReportStatus.PROCESSING,
    };

    act(() => {
      useReportsStore.getState().addExecution(execA);
      useReportsStore.getState().addExecution(execB);
    });

    expect(useReportsStore.getState().executions['REPLOG-A'].status).toBe(ReportStatus.QUEUED);
    expect(useReportsStore.getState().executions['REPLOG-B'].status).toBe(ReportStatus.PROCESSING);

    act(() => {
      useReportsStore.getState().updateExecutionStatus('REPLOG-A', ReportStatus.COMPLETED);
    });

    expect(useReportsStore.getState().executions['REPLOG-A'].status).toBe(ReportStatus.COMPLETED);
    expect(useReportsStore.getState().executions['REPLOG-B'].status).toBe(ReportStatus.PROCESSING);
  });

  it('3. polling starts for QUEUED and transitions through PROCESSING to COMPLETED and stops', async () => {
    const execProcessing = {
      execution_id: 'REPLOG-POLL-1',
      report_id: 'site_operations',
      report_type: 'site',
      format: ReportFormat.PDF,
      requested_by: 'user',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 10,
      status: ReportStatus.PROCESSING,
    };

    const execCompleted = { ...execProcessing, status: ReportStatus.COMPLETED };

    (reportsApiClient.getExecutionStatus as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(execProcessing)
      .mockResolvedValueOnce(execCompleted);

    const onCompleteMock = vi.fn();

    const { result } = renderHook(() =>
      useReportExecutionPoll({
        executionId: 'REPLOG-POLL-1',
        intervalMs: 1000,
        onComplete: onCompleteMock,
      })
    );

    // Initial poll invocation
    await act(async () => {
      await Promise.resolve();
    });

    expect(reportsApiClient.getExecutionStatus).toHaveBeenCalledTimes(1);
    expect(useReportsStore.getState().executions['REPLOG-POLL-1'].status).toBe(ReportStatus.PROCESSING);

    // Fast forward timer to trigger second poll
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    expect(reportsApiClient.getExecutionStatus).toHaveBeenCalledTimes(2);
    expect(useReportsStore.getState().executions['REPLOG-POLL-1'].status).toBe(ReportStatus.COMPLETED);
    expect(onCompleteMock).toHaveBeenCalledWith(execCompleted);
    expect(result.current.isTerminal).toBe(true);
  });

  it('4. polling stops immediately on NO_DATA status without error', async () => {
    const execNoData = {
      execution_id: 'REPLOG-NODATA-1',
      report_id: 'alerts_incidents',
      report_type: 'alerts',
      format: ReportFormat.JSON,
      requested_by: 'user',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 0,
      status: ReportStatus.NO_DATA,
    };

    (reportsApiClient.getExecutionStatus as ReturnType<typeof vi.fn>).mockResolvedValueOnce(execNoData);

    const { result } = renderHook(() =>
      useReportExecutionPoll({ executionId: 'REPLOG-NODATA-1', intervalMs: 1000 })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.execution?.status).toBe(ReportStatus.NO_DATA);
    expect(result.current.isTerminal).toBe(true);
  });

  it('5. cleans up timers on unmount', async () => {
    const execQueued = {
      execution_id: 'REPLOG-UNMOUNT',
      report_id: 'site_operations',
      report_type: 'site',
      format: ReportFormat.PDF,
      requested_by: 'user',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 0,
      status: ReportStatus.QUEUED,
    };

    (reportsApiClient.getExecutionStatus as ReturnType<typeof vi.fn>).mockResolvedValue(execQueued);

    const { unmount } = renderHook(() =>
      useReportExecutionPoll({ executionId: 'REPLOG-UNMOUNT', intervalMs: 1000 })
    );

    await act(async () => {
      await Promise.resolve();
    });

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });

    // Should not continue polling after unmount
    expect(reportsApiClient.getExecutionStatus).toHaveBeenCalledTimes(1);
  });

  it('6. correctly identifies all terminal status values', () => {
    expect(isTerminalStatus(ReportStatus.COMPLETED)).toBe(true);
    expect(isTerminalStatus(ReportStatus.NO_DATA)).toBe(true);
    expect(isTerminalStatus(ReportStatus.FAILED)).toBe(true);
    expect(isTerminalStatus(ReportStatus.PURGED)).toBe(true);
    expect(isTerminalStatus(ReportStatus.SCOPE_VALIDATION_FAILED)).toBe(true);
    expect(isTerminalStatus(ReportStatus.PROCESSING)).toBe(false);
    expect(isTerminalStatus(ReportStatus.QUEUED)).toBe(false);
  });
});
