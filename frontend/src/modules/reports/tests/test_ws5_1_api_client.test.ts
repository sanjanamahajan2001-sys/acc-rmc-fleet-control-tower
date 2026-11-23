import { describe, it, expect, vi, beforeEach } from 'vitest';
import { reportsApiClient } from '../api/reports.api';
import { apiClient } from '../../../api/client';
import { ReportFormat, ReportStatus, ScopeValidationStatus } from '../types/report.types';

vi.mock('../../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('WS5.1 - Reporting API Client & DTO Contracts Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. listReports requests GET /reports and returns catalog', async () => {
    const mockCatalog = [
      {
        report_id: 'site_operations',
        title: 'Site Operations Dashboard',
        description: 'Site operations summary',
        source_service: 'site_dashboard',
        supported_formats: [ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.JSON],
        category: 'OPERATIONAL',
        permission_role: 'VIEWER',
        is_active: true,
      },
    ];
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockCatalog });

    const result = await reportsApiClient.listReports();
    expect(apiClient.get).toHaveBeenCalledWith('/reports');
    expect(result).toEqual(mockCatalog);
    expect(result[0].report_id).toBe('site_operations');
  });

  it('2. getReportDefinition requests GET /reports/{id}', async () => {
    const mockDefinition = {
      report_id: 'fleet_operations',
      title: 'Fleet Operations Dashboard',
      description: 'Fleet metrics',
      source_service: 'fleet_dashboard',
      supported_formats: [ReportFormat.PDF],
      category: 'FLEET',
      permission_role: 'VIEWER',
      is_active: true,
    };
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockDefinition });

    const result = await reportsApiClient.getReportDefinition('fleet_operations');
    expect(apiClient.get).toHaveBeenCalledWith('/reports/fleet_operations');
    expect(result).toEqual(mockDefinition);
  });

  it('3. generateReport requests POST /reports/generate with exact serialization', async () => {
    const mockResponse = {
      execution_id: 'REPLOG-123456789012',
      report_id: 'site_operations',
      report_type: 'site_dashboard',
      format: ReportFormat.PDF,
      requested_by: 'test_user',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: { plant_id: 'VASCO', operation_date: '2026-08-05' },
      effective_scope: { plant_id: 'VASCO', operation_date: '2026-08-05' },
      scope_fingerprint: 'fp-123',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 50,
      status: ReportStatus.COMPLETED,
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

    const payload = {
      report_id: 'site_operations',
      format: ReportFormat.PDF,
      scope: { plant_id: 'VASCO', operation_date: '2026-08-05' },
      requested_by: 'test_user',
    };

    const result = await reportsApiClient.generateReport(payload);
    expect(apiClient.post).toHaveBeenCalledWith('/reports/generate', payload);
    expect(result.status).toBe(ReportStatus.COMPLETED);
    expect(result.execution_id).toBe('REPLOG-123456789012');
  });

  it('4. generateReportAsync requests POST /reports/generate-async (HTTP 202)', async () => {
    const mockResponse = {
      execution_id: 'REPLOG-async-123',
      report_id: 'site_comparison',
      report_type: 'site_dashboard',
      format: ReportFormat.XLSX,
      requested_by: 'async_user',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp-async',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 0,
      status: ReportStatus.QUEUED,
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

    const payload = {
      report_id: 'site_comparison',
      format: ReportFormat.XLSX,
      scope: {},
      requested_by: 'async_user',
    };

    const result = await reportsApiClient.generateReportAsync(payload);
    expect(apiClient.post).toHaveBeenCalledWith('/reports/generate-async', payload);
    expect(result.status).toBe(ReportStatus.QUEUED);
  });

  it('5. getExecutionStatus requests GET /reports/executions/{id}/status', async () => {
    const mockResponse = {
      execution_id: 'REPLOG-999',
      report_id: 'dispatch_optimization',
      report_type: 'dispatch',
      format: ReportFormat.PDF,
      requested_by: 'poll_user',
      requested_at: '2026-08-20T12:00:00Z',
      requested_scope: {},
      effective_scope: {},
      scope_fingerprint: 'fp-999',
      scope_validation_status: ScopeValidationStatus.VALIDATED,
      record_count: 15,
      status: ReportStatus.PROCESSING,
    };
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

    const result = await reportsApiClient.getExecutionStatus('REPLOG-999');
    expect(apiClient.get).toHaveBeenCalledWith('/reports/executions/REPLOG-999/status');
    expect(result.status).toBe(ReportStatus.PROCESSING);
  });

  it('6. getDownloadToken requests POST /reports/executions/{id}/download-token', async () => {
    const mockToken = {
      execution_id: 'REPLOG-tok-1',
      format: 'pdf',
      download_token: 'signed_jwt_token_sample',
      expires_in_minutes: 15,
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockToken });

    const result = await reportsApiClient.getDownloadToken('REPLOG-tok-1', ReportFormat.PDF);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/reports/executions/REPLOG-tok-1/download-token',
      null,
      { params: { format: 'pdf' } }
    );
    expect(result.download_token).toBe('signed_jwt_token_sample');
  });

  it('7. downloadArtifact requests GET /reports/executions/{id}/download with responseType blob', async () => {
    const mockBlob = new Blob(['PDF_BINARY_CONTENT'], { type: 'application/pdf' });
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockBlob });

    const result = await reportsApiClient.downloadArtifact('REPLOG-dl-1', 'pdf', 'sample_token');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/reports/executions/REPLOG-dl-1/download',
      {
        params: { format: 'pdf', token: 'sample_token' },
        responseType: 'blob',
      }
    );
    expect(result).toEqual(mockBlob);
  });

  it('8. preserves NO_DATA and FAILED execution status semantics', async () => {
    const mockNoData = {
      execution_id: 'REPLOG-nodata',
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
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockNoData });

    const res = await reportsApiClient.getExecutionStatus('REPLOG-nodata');
    expect(res.status).toBe(ReportStatus.NO_DATA);
    expect(res.record_count).toBe(0);
  });
});
