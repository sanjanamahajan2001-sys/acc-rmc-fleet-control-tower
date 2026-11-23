import { create } from 'zustand';
import {
  ReportDefinitionDTO,
  ReportExecutionResponse,
  ReportStatus,
} from '../types/report.types';
import { reportsApiClient } from '../api/reports.api';

export interface ReportPollingInfo {
  isPolling: boolean;
  error?: string | null;
  lastPolledAt?: string | null;
}

export interface ReportsState {
  catalog: ReportDefinitionDTO[];
  isCatalogLoading: boolean;
  catalogError: string | null;

  executions: Record<string, ReportExecutionResponse>;
  pollingMap: Record<string, ReportPollingInfo>;

  loadCatalog: () => Promise<void>;
  addExecution: (execution: ReportExecutionResponse) => void;
  updateExecution: (execution: ReportExecutionResponse) => void;
  updateExecutionStatus: (
    executionId: string,
    status: ReportStatus,
    extra?: Partial<ReportExecutionResponse>
  ) => void;

  setPollingState: (executionId: string, isPolling: boolean, error?: string | null) => void;
  clearExecution: (executionId: string) => void;
}

export const useReportsStore = create<ReportsState>((set) => ({

  catalog: [],
  isCatalogLoading: false,
  catalogError: null,

  executions: {},
  pollingMap: {},

  loadCatalog: async () => {
    set({ isCatalogLoading: true, catalogError: null });
    try {
      const catalog = await reportsApiClient.listReports();
      set({ catalog, isCatalogLoading: false });
    } catch (err: any) {
      set({
        catalogError: err.message || 'Failed to load report catalog',
        isCatalogLoading: false,
      });
    }
  },

  addExecution: (execution: ReportExecutionResponse) => {
    set((state) => ({
      executions: { ...state.executions, [execution.execution_id]: execution },
    }));
  },

  updateExecution: (execution: ReportExecutionResponse) => {
    set((state) => ({
      executions: { ...state.executions, [execution.execution_id]: execution },
    }));
  },

  updateExecutionStatus: (executionId, status, extra) => {
    set((state) => {
      const existing = state.executions[executionId];
      if (!existing) return state;
      return {
        executions: {
          ...state.executions,
          [executionId]: {
            ...existing,
            ...extra,
            status,
          },
        },
      };
    });
  },

  setPollingState: (executionId, isPolling, error = null) => {
    set((state) => ({
      pollingMap: {
        ...state.pollingMap,
        [executionId]: {
          isPolling,
          error,
          lastPolledAt: new Date().toISOString(),
        },
      },
    }));
  },

  clearExecution: (executionId) => {
    set((state) => {
      const nextExecutions = { ...state.executions };
      delete nextExecutions[executionId];
      const nextPolling = { ...state.pollingMap };
      delete nextPolling[executionId];
      return { executions: nextExecutions, pollingMap: nextPolling };
    });
  },
}));
