import { useEffect, useRef, useCallback } from 'react';
import { useReportsStore } from '../store/reports.store';
import { reportsApiClient } from '../api/reports.api';
import { ReportStatus, ReportExecutionResponse } from '../types/report.types';

export interface UseReportExecutionPollOptions {
  executionId?: string | null;
  enabled?: boolean;
  intervalMs?: number;
  onComplete?: (execution: ReportExecutionResponse) => void;
  onError?: (error: any) => void;
}

export const TERMINAL_STATUSES: ReportStatus[] = [
  ReportStatus.COMPLETED,
  ReportStatus.NO_DATA,
  ReportStatus.FAILED,
  ReportStatus.PURGED,
  ReportStatus.SCOPE_VALIDATION_FAILED,
];

export const isTerminalStatus = (status: ReportStatus): boolean => {
  return TERMINAL_STATUSES.includes(status);
};

export const useReportExecutionPoll = ({
  executionId,
  enabled = true,
  intervalMs = 2000,
  onComplete,
  onError,
}: UseReportExecutionPollOptions) => {
  const storeExecution = useReportsStore((s) => (executionId ? s.executions[executionId] : null));
  const pollingInfo = useReportsStore((s) => (executionId ? s.pollingMap[executionId] : null));
  const setPollingState = useReportsStore((s) => s.setPollingState);
  const updateExecution = useReportsStore((s) => s.updateExecution);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef<boolean>(true);
  const currentExecutionIdRef = useRef<string | null>(executionId || null);

  currentExecutionIdRef.current = executionId || null;

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (executionId) {
      setPollingState(executionId, false, null);
    }
  }, [executionId, setPollingState]);

  const pollOnce = useCallback(async () => {
    if (!executionId || !enabled || !isMountedRef.current) return;

    try {
      setPollingState(executionId, true, null);
      const latestExecution = await reportsApiClient.getExecutionStatus(executionId);

      if (!isMountedRef.current || currentExecutionIdRef.current !== executionId) {
        return;
      }

      updateExecution(latestExecution);

      if (isTerminalStatus(latestExecution.status)) {
        stopPolling();
        if (onComplete) onComplete(latestExecution);
      } else {
        timerRef.current = setTimeout(pollOnce, intervalMs);
      }
    } catch (err: any) {
      if (!isMountedRef.current || currentExecutionIdRef.current !== executionId) return;

      const errorMessage = err.message || 'Polling error occurred';
      setPollingState(executionId, false, errorMessage);
      if (onError) onError(err);
      
      // Retain polling on transient errors unless unmounted or disabled
      timerRef.current = setTimeout(pollOnce, intervalMs * 1.5);
    }
  }, [executionId, enabled, intervalMs, updateExecution, setPollingState, stopPolling, onComplete, onError]);

  useEffect(() => {
    isMountedRef.current = true;

    if (!executionId || !enabled) {
      stopPolling();
      return;
    }

    const currentStatus = storeExecution?.status;
    if (currentStatus && isTerminalStatus(currentStatus)) {
      setPollingState(executionId, false, null);
      return;
    }

    pollOnce();

    return () => {
      isMountedRef.current = false;
      stopPolling();
    };
  }, [executionId, enabled]);

  return {
    execution: storeExecution,
    isPolling: Boolean(pollingInfo?.isPolling),
    pollingError: pollingInfo?.error || null,
    isTerminal: Boolean(storeExecution?.status && isTerminalStatus(storeExecution.status)),
    stopPolling,
  };
};
