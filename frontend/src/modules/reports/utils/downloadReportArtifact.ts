import { reportsApiClient } from '../api/reports.api';
import { ReportFormat } from '../types/report.types';

export interface DownloadReportArtifactOptions {
  executionId: string;
  format: ReportFormat | string;
  reportId?: string;
  onSuccess?: () => void;
  onError?: (error: any) => void;
}

export const downloadReportArtifact = async ({
  executionId,
  format,
  reportId,
  onSuccess,
  onError,
}: DownloadReportArtifactOptions): Promise<void> => {
  try {
    const fmtStr = typeof format === 'string' ? format.toLowerCase() : String(format).toLowerCase();

    // 1. Get short-lived download token
    const tokenResponse = await reportsApiClient.getDownloadToken(executionId, fmtStr);

    // 2. Fetch binary blob using token
    const rawBlob = await reportsApiClient.downloadArtifact(
      executionId,
      fmtStr,
      tokenResponse.download_token
    );

    // Enforce explicit binary MIME type to prevent browser download truncation
    let mimeType = rawBlob.type;
    if (fmtStr === 'pdf') {
      mimeType = 'application/pdf';
    } else if (fmtStr === 'xlsx') {
      mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    } else if (fmtStr === 'json') {
      mimeType = 'application/json';
    }
    const blob = new Blob([rawBlob], { type: mimeType });

    // 3. Construct object URL and trigger download
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    const fallbackName = (reportId || 'report') + '_' + executionId + '.' + fmtStr;
    link.setAttribute('download', fallbackName);

    document.body.appendChild(link);
    link.click();

    // 4. Cleanup DOM immediately, but delay revoking object URL by 60s
    // to give browser download manager time to stream all bytes without truncating
    document.body.removeChild(link);
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
    }, 60000);

    if (onSuccess) onSuccess();
  } catch (err: any) {
    if (onError) onError(err);
    throw err;
  }
};

export const previewReportArtifact = async ({
  executionId,
  format = 'pdf',
  reportId,
  onSuccess,
  onError,
}: {
  executionId: string;
  format?: ReportFormat | string;
  reportId?: string;
  onSuccess?: () => void;
  onError?: (error: any) => void;
}): Promise<void> => {
  try {
    const fmtStr = typeof format === 'string' ? format.toLowerCase() : String(format).toLowerCase();

    // 1. Get short-lived download token
    const tokenResponse = await reportsApiClient.getDownloadToken(executionId, fmtStr);

    // 2. Fetch binary blob using token
    const rawBlob = await reportsApiClient.downloadArtifact(
      executionId,
      fmtStr,
      tokenResponse.download_token
    );

    // Enforce strict application/pdf MIME type
    const blob = new Blob([rawBlob], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);

    // Open top-level native browser PDF viewer tab directly
    // This allows the browser PDF toolbar (Print / Save As) to operate on the raw PDF binary stream directly,
    // avoiding empty or damaged raster prints caused by HTML iframe containment.
    const previewWindow = window.open(url, '_blank');
    if (!previewWindow) {
      window.location.href = url;
    }

    // Keep blob alive in memory for 10 minutes so users can view, print, and save without timeout
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
    }, 600000);

    if (onSuccess) onSuccess();
  } catch (err: any) {
    if (onError) onError(err);
    throw err;
  }
};
