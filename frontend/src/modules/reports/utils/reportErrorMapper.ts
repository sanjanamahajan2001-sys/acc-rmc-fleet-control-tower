import { ReportStatus, ReportExecutionResponse } from '../types/report.types';

export interface UserFacingErrorDetails {
  title: string;
  message: string;
  category: 'VALIDATION' | 'NO_DATA' | 'RATE_LIMIT' | 'AUTH' | 'NOT_FOUND' | 'SERVER' | 'NETWORK';
  isRetryable: boolean;
}

export const mapReportErrorToUserMessage = (
  errorOrStatus: any | ReportStatus,
  execution?: ReportExecutionResponse | null
): UserFacingErrorDetails => {
  // Check if string status passed directly
  if (typeof errorOrStatus === 'string') {
    switch (errorOrStatus) {
      case ReportStatus.NO_DATA:
        return {
          title: 'No Data Found',
          message: 'No authoritative records matched the requested scope criteria.',
          category: 'NO_DATA',
          isRetryable: false,
        };
      case ReportStatus.SCOPE_VALIDATION_FAILED:
        return {
          title: 'Invalid Scope Parameters',
          message: execution?.error_message || 'The specified filter parameters are invalid for this report.',
          category: 'VALIDATION',
          isRetryable: false,
        };
      case ReportStatus.FAILED:
        return {
          title: 'Report Generation Failed',
          message: execution?.error_message || 'Report execution encountered an internal error.',
          category: 'SERVER',
          isRetryable: true,
        };
      case ReportStatus.PURGED:
        return {
          title: 'Artifact Purged',
          message: 'The requested report artifact has expired and been purged from storage.',
          category: 'NOT_FOUND',
          isRetryable: false,
        };
    }
  }

  // Handle API / HTTP Error Objects
  const code = errorOrStatus?.code || errorOrStatus?.response?.data?.error?.code || '';
  const status = errorOrStatus?.status || errorOrStatus?.response?.status;
  const message = errorOrStatus?.message || errorOrStatus?.response?.data?.error?.message || '';

  if (code === 'EXPORT_LIMIT_EXCEEDED' || message.includes('EXPORT_LIMIT_EXCEEDED')) {
    return {
      title: 'Export Record Limit Exceeded',
      message: 'The requested scope returned more than 10,000 records. Please narrow your filter scope.',
      category: 'VALIDATION',
      isRetryable: false,
    };
  }

  if (status === 429 || code === 'RATE_LIMIT_EXCEEDED') {
    return {
      title: 'Rate Limit Exceeded',
      message: 'Too many requests submitted. Please wait a moment before trying again.',
      category: 'RATE_LIMIT',
      isRetryable: true,
    };
  }

  if (status === 401 || status === 403) {
    return {
      title: 'Authorization Required',
      message: 'You do not have permission to view or export this report.',
      category: 'AUTH',
      isRetryable: false,
    };
  }

  if (status === 404 || code === 'REPORT_NOT_FOUND' || code === 'REPORT_ARTIFACT_NOT_FOUND') {
    return {
      title: 'Report Not Found',
      message: 'The requested report or artifact file could not be found.',
      category: 'NOT_FOUND',
      isRetryable: false,
    };
  }

  return {
    title: 'Execution Error',
    message: message || 'An unexpected error occurred during report processing.',
    category: 'SERVER',
    isRetryable: true,
  };
};
