import { env } from '../../../config/env';
/**
 * ERP Module Zustand State Stores
 * Dedicated reactive stores for Upload, Progress (SSE), Jobs, Statistics, and Notifications.
 */

import { create } from 'zustand';
import {
  AuditLogItem,
  ERPImportStatistics,
  ImportJobResponse,
  ImportProgressSnapshot,
  VersionedSSEEvent,
} from '../types';
import { erpApiClient } from '../api';

// =============================================================================
// 1. UPLOAD STORE
// =============================================================================
interface UploadState {
  uploading: boolean;
  activeJob: ImportJobResponse | null;
  error: string | null;
  uploadFile: (file: File) => Promise<ImportJobResponse | null>;
  resetUpload: () => void;
}

export const useERPUploadStore = create<UploadState>((set) => ({
  uploading: false,
  activeJob: null,
  error: null,
  uploadFile: async (file: File) => {
    set({ uploading: true, error: null });
    try {
      const job = await erpApiClient.uploadWorkbook(file);
      set({ uploading: false, activeJob: job });
      return job;
    } catch (err: any) {
      set({ uploading: false, error: err.message || 'Upload failed' });
      return null;
    }
  },
  resetUpload: () => set({ uploading: false, activeJob: null, error: null }),
}));


// =============================================================================
// 2. PROGRESS (SSE) STORE
// =============================================================================
interface ProgressState {
  snapshot: ImportProgressSnapshot | null;
  isStreaming: boolean;
  activeJobId: string | null;
  connectSSE: (jobId: string) => void;
  disconnectSSE: () => void;
}

let eventSourceInstance: EventSource | null = null;

export const useERPProgressStore = create<ProgressState>((set, get) => ({
  snapshot: null,
  isStreaming: false,
  activeJobId: null,

  connectSSE: (jobId: string) => {
    get().disconnectSSE();

    const DEV_DEFAULT_TOKEN =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJqdGkiOiJlMjFmMWNjMS0xZGQ3LTQ3MmYtOGFkNC0yMmM5MzBmOTJhZjciLCJ0eXBlIjoiYWNjZXNzIiwidGVuYW50X2lkIjpudWxsLCJwbGFudF9pZCI6bnVsbCwiaWF0IjoxNzg1OTM0MDY1LCJleHAiOjIxMDEyOTQwNjV9.s0UWK7qNVX_dxvYZnfWO0NT3ph4qzTwU2Z2LrlMUeQY';
    const token =
      localStorage.getItem('fct_auth_token') ||
      localStorage.getItem('token') ||
      DEV_DEFAULT_TOKEN;

    const sseUrl = `${env.VITE_API_BASE_URL}/erp/jobs/${jobId}/progress?token=${encodeURIComponent(token)}`;

    eventSourceInstance = new EventSource(sseUrl);
    set({ isStreaming: true, activeJobId: jobId });

    eventSourceInstance.addEventListener('erp.import.progress.v1', (event: MessageEvent) => {
      try {
        const payload: VersionedSSEEvent = JSON.parse(event.data);
        set({ snapshot: payload.snapshot });

        if (
          payload.snapshot.stage === 'COMPLETED' ||
          payload.snapshot.stage === 'FAILED' ||
          payload.snapshot.stage === 'CANCELLED'
        ) {
          get().disconnectSSE();
          useERPJobsStore.getState().fetchJobs();
          useERPStatisticsStore.getState().fetchStatistics();
        }
      } catch (err) {
        console.error('Failed to parse SSE payload:', err);
      }
    });

    eventSourceInstance.onerror = () => {
      get().disconnectSSE();
    };
  },

  disconnectSSE: () => {
    if (eventSourceInstance) {
      eventSourceInstance.close();
      eventSourceInstance = null;
    }
    set({ isStreaming: false, activeJobId: null });
  },
}));


// =============================================================================
// 3. JOBS STORE
// =============================================================================
interface JobsState {
  jobs: ImportJobResponse[];
  totalRecords: number;
  currentPage: number;
  loading: boolean;
  error: string | null;
  fetchJobs: (page?: number, status?: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  retryJob: (jobId: string) => Promise<void>;
  revertDataset: (params: { dataset_period?: string; period_key?: string; job_number?: string }) => Promise<any>;
}

export const useERPJobsStore = create<JobsState>((set, get) => ({
  jobs: [],
  totalRecords: 0,
  currentPage: 1,
  loading: false,
  error: null,

  fetchJobs: async (page = 1, status?: string) => {
    set({ loading: true, error: null });
    try {
      const res = await erpApiClient.listJobs(page, 100, status);
      set({
        jobs: res.items,
        totalRecords: res.total_records,
        currentPage: res.page,
        loading: false,
      });
    } catch (err: any) {
      set({ loading: false, error: err.message || 'Failed to fetch jobs' });
    }
  },

  cancelJob: async (jobId: string) => {
    try {
      await erpApiClient.cancelJob(jobId);
      await get().fetchJobs(get().currentPage);
    } catch (err: any) {
      set({ error: err.message || 'Cancel failed' });
    }
  },

  retryJob: async (jobId: string) => {
    try {
      await erpApiClient.retryJob(jobId);
      await get().fetchJobs(get().currentPage);
    } catch (err: any) {
      set({ error: err.message || 'Retry failed' });
    }
  },

  revertDataset: async (params: { dataset_period?: string; period_key?: string; job_number?: string }) => {
    set({ loading: true, error: null });
    try {
      const res = await erpApiClient.revertDataset(params);
      await get().fetchJobs(1);
      window.dispatchEvent(new CustomEvent('fleet-dataset-updated'));
      return res;
    } catch (err: any) {
      set({ loading: false, error: err.message || 'Dataset revert failed' });
      throw err;
    }
  },
}));


// =============================================================================
// 4. STATISTICS & AUDIT STORE
// =============================================================================
interface StatisticsState {
  statistics: ERPImportStatistics | null;
  auditLogs: AuditLogItem[];
  loading: boolean;
  fetchStatistics: () => Promise<void>;
  fetchAuditLogs: () => Promise<void>;
}

export const useERPStatisticsStore = create<StatisticsState>((set) => ({
  statistics: null,
  auditLogs: [],
  loading: false,

  fetchStatistics: async () => {
    try {
      const stats = await erpApiClient.getStatistics();
      set({ statistics: stats });
    } catch (err) {
      console.error('Failed to fetch statistics:', err);
    }
  },

  fetchAuditLogs: async () => {
    try {
      const logsRes = await erpApiClient.getAuditLogs(1, 20);
      set({ auditLogs: logsRes.items });
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    }
  },
}));


// =============================================================================
// 5. NOTIFICATIONS STORE
// =============================================================================
export interface NotificationItem {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  timestamp: string;
}

interface NotificationsState {
  notifications: NotificationItem[];
  addNotification: (type: NotificationItem['type'], message: string) => void;
  removeNotification: (id: string) => void;
}

export const useERPNotificationStore = create<NotificationsState>((set) => ({
  notifications: [],
  addNotification: (type, message) => {
    const item: NotificationItem = {
      id: Math.random().toString(36).substring(2, 9),
      type,
      message,
      timestamp: new Date().toLocaleTimeString(),
    };
    set((state) => ({ notifications: [item, ...state.notifications].slice(0, 5) }));
  },
  removeNotification: (id) =>
    set((state) => ({ notifications: state.notifications.filter((n) => n.id !== id) })),
}));
