import { env } from '../../../config/env';
/**
 * ERP Module API Client Service
 * Consumes WS1.6 REST API endpoints and maps them to APIResponse envelopes.
 */

import axios from 'axios';
import {
  AuditLogItem,
  ERPImportStatistics,
  ImportJobResponse,
  JobActionResponse,
  PaginatedResponse,
} from '../types';
import { APP_CONSTANTS } from '../../../config/constants';

const API_BASE_URL = env.VITE_API_BASE_URL + '/erp';

// Fallback development JWT token generated using backend JWT_SECRET_KEY
const DEV_DEFAULT_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJqdGkiOiJjY2VjMzcwNS1hZWM0LTQxZjgtYTM5ZC04NTJlYTUxZjEzYTkiLCJ0eXBlIjoiYWNjZXNzIiwidGVuYW50X2lkIjpudWxsLCJwbGFudF9pZCI6bnVsbCwiaWF0IjoxNzg2NjEyMzU4LCJleHAiOjIxMDE5NzIzNTh9.lxfl9aoDa4majrYQY_AMVMk-Sx9r4UOTK7S07iC0gB8';

function getAuthHeader(): string {
  const token =
    localStorage.getItem(APP_CONSTANTS.STORAGE_KEYS.AUTH_TOKEN) ||
    localStorage.getItem('token') ||
    DEV_DEFAULT_TOKEN;
  return 'Bearer ' + token;
}

export const erpApiClient = {
  /**
   * Upload an ERP Excel workbook or raw telemetry CSV/JSON
   */
  async uploadWorkbook(file: File): Promise<ImportJobResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const targetUrl = API_BASE_URL + '/workbooks/upload';

    try {
      const response = await axios.post(targetUrl, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: getAuthHeader(),
        },
      });

      return response.data.data;
    } catch (err: any) {
      const serverMsg =
        err.response?.data?.error?.message || err.response?.data?.detail || err.message || 'File upload failed';
      throw new Error(serverMsg);
    }
  },

  /**
   * List and filter Import Jobs
   */
  async listJobs(page = 1, pageSize = 20, status?: string): Promise<PaginatedResponse<ImportJobResponse>> {
    const response = await axios.get(API_BASE_URL + '/jobs', {
      params: { page, page_size: pageSize, status },
      headers: {
        Authorization: getAuthHeader(),
      },
    });
    return response.data.data;
  },

  /**
   * Get single job details
   */
  async getJobDetails(jobId: string): Promise<ImportJobResponse> {
    const response = await axios.get(API_BASE_URL + '/jobs/' + jobId, {
      headers: {
        Authorization: getAuthHeader(),
      },
    });
    return response.data.data;
  },

  /**
   * Cancel an active import job
   */
  async cancelJob(jobId: string): Promise<JobActionResponse> {
    const response = await axios.post(
      API_BASE_URL + '/jobs/' + jobId + '/cancel',
      {},
      {
        headers: {
          Authorization: getAuthHeader(),
        },
      }
    );
    return response.data.data;
  },

  /**
   * Retry a failed import job
   */
  async retryJob(jobId: string): Promise<JobActionResponse> {
    const response = await axios.post(
      API_BASE_URL + '/jobs/' + jobId + '/retry',
      {},
      {
        headers: {
          Authorization: getAuthHeader(),
        },
      }
    );
    return response.data.data;
  },

  /**
   * Fetch platform import statistics
   */
  async getStatistics(): Promise<ERPImportStatistics> {
    const response = await axios.get(API_BASE_URL + '/statistics', {
      headers: {
        Authorization: getAuthHeader(),
      },
    });
    return response.data.data;
  },

  /**
   * Fetch audit logs
   */
  async getAuditLogs(page = 1, pageSize = 50): Promise<PaginatedResponse<AuditLogItem>> {
    const response = await axios.get(API_BASE_URL + '/audit-logs', {
      params: { page, page_size: pageSize },
      headers: {
        Authorization: getAuthHeader(),
      },
    });
    return response.data.data;
  },

  /**
   * Fetch Data Explorer records for any domain entity
   */
  async getExplorerData(entity: string, page = 1, pageSize = 20): Promise<PaginatedResponse<any>> {
    const url = entity === 'telemetry' ? env.VITE_API_BASE_URL + '/telemetry/explorer/metrics' : API_BASE_URL + '/explorer/' + entity;
    const response = await axios.get(url, {
      params: { page, page_size: pageSize },
      headers: {
        Authorization: getAuthHeader(),
      },
    });
    return response.data.data;
  },

  /**
   * Reset Demo ERP Data (Admin Only)
   */
  async resetDemoData(): Promise<any> {
    const response = await axios.post(
      API_BASE_URL + '/admin/reset-demo-data',
      {},
      {
        headers: {
          Authorization: getAuthHeader(),
        },
      }
    );
    return response.data.data;
  },

  /**
   * Revert to an archived dataset (Resumes operational state from selected dataset)
   */
  async revertDataset(params: { dataset_period?: string; period_key?: string; job_number?: string }): Promise<any> {
    try {
      const response = await axios.post(
        API_BASE_URL + '/admin/revert-dataset',
        params,
        {
          headers: {
            Authorization: getAuthHeader(),
          },
        }
      );
      return response.data.data;
    } catch (err: any) {
      const serverMsg =
        err.response?.data?.error?.message || err.response?.data?.detail || err.message || 'Dataset revert failed';
      throw new Error(serverMsg);
    }
  },
};
