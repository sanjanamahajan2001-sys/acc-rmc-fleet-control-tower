import { env } from '../../../config/env';
import { apiClient } from '../../../api/client';
import {
  ReportDefinitionDTO,
  ReportRequestDTO,
  ReportExecutionResponse,
  DownloadTokenResponse,
  ReportFormat,
} from '../types/report.types';

export const reportsApiClient = {
  /**
   * GET ${env.VITE_API_BASE_URL}/reports
   * Fetches full catalog of registered reports.
   */
  async listReports(): Promise<ReportDefinitionDTO[]> {
    const response = await apiClient.get<any[]>('/reports');
    return response.data.map((item) => ({
      report_id: item.report_id,
      title: item.title || item.name || item.report_id,
      description: item.description || '',
      source_service: item.source_service || 'reporting',
      supported_formats: item.supported_formats || [ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
      category: item.category || 'GENERAL',
      permission_role: item.permission_role || 'VIEWER',
      is_active: item.is_active !== undefined ? item.is_active : true,
    }));
  },

  /**
   * GET ${env.VITE_API_BASE_URL}/reports/{report_id}
   * Fetches definition for a specific registered report.
   */
  async getReportDefinition(reportId: string): Promise<ReportDefinitionDTO> {
    const response = await apiClient.get<any>('/reports/' + reportId);
    const item = response.data;
    return {
      report_id: item.report_id,
      title: item.title || item.name || item.report_id,
      description: item.description || '',
      source_service: item.source_service || 'reporting',
      supported_formats: item.supported_formats || [ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
      category: item.category || 'GENERAL',
      permission_role: item.permission_role || 'VIEWER',
      is_active: item.is_active !== undefined ? item.is_active : true,
    };
  },


  /**
   * POST ${env.VITE_API_BASE_URL}/reports/generate
   * Executes synchronous report generation.
   */
  async generateReport(dto: ReportRequestDTO): Promise<ReportExecutionResponse> {
    const response = await apiClient.post<ReportExecutionResponse>('/reports/generate', dto);
    return response.data;
  },

  /**
   * POST ${env.VITE_API_BASE_URL}/reports/generate-async
   * Submits report generation task for background execution (HTTP 202).
   */
  async generateReportAsync(dto: ReportRequestDTO): Promise<ReportExecutionResponse> {
    const response = await apiClient.post<ReportExecutionResponse>('/reports/generate-async', dto);
    return response.data;
  },

  /**
   * GET ${env.VITE_API_BASE_URL}/reports/executions/{execution_id}/status
   * Polls execution status and lifecycle details for an execution ID.
   */
  async getExecutionStatus(executionId: string): Promise<ReportExecutionResponse> {
    const response = await apiClient.get<ReportExecutionResponse>(
      '/reports/executions/' + executionId + '/status'
    );
    return response.data;
  },

  /**
   * GET ${env.VITE_API_BASE_URL}/reports/executions
   * Lists historical report execution records.
   */
  async listExecutions(limit = 50, offset = 0): Promise<ReportExecutionResponse[]> {
    const response = await apiClient.get<ReportExecutionResponse[]>('/reports/executions', {
      params: { limit, offset },
    });
    return response.data;
  },

  /**
   * POST ${env.VITE_API_BASE_URL}/reports/executions/{execution_id}/download-token
   * Generates a short-lived, signed download token for authorized artifact acquisition.
   */
  async getDownloadToken(
    executionId: string,
    format: ReportFormat | string = 'pdf',
    userId?: string
  ): Promise<DownloadTokenResponse> {
    const response = await apiClient.post<DownloadTokenResponse>(
      '/reports/executions/' + executionId + '/download-token',
      null,
      {
        params: {
          format: String(format).toLowerCase(),
          ...(userId ? { user_id: userId } : {}),
        },
      }
    );
    return response.data;
  },

  /**
   * GET ${env.VITE_API_BASE_URL}/reports/executions/{execution_id}/download
   * Acquires rendered binary artifact bytes using optional download token.
   */
  async downloadArtifact(
    executionId: string,
    format: ReportFormat | string = 'pdf',
    token?: string
  ): Promise<Blob> {
    const response = await apiClient.get<Blob>('/reports/executions/' + executionId + '/download', {
      params: {
        format: String(format).toLowerCase(),
        ...(token ? { token } : {}),
      },
      responseType: 'blob',
    });
    return response.data;
  },

};
