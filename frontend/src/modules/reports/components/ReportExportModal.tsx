import { formatDisplayDate } from '../../../utils/date';
import React, { useState, useEffect } from 'react';
import { Modal } from '../../../components/overlays/Modal';
import { Button } from '../../../components/inputs/Button';
import { Select } from '../../../components/inputs/Select';
import {
  ReportDefinitionDTO,
  ReportFormat,
  ReportScopeDTO,
  ReportStatus,
  ReportExecutionResponse,
} from '../types/report.types';
import { reportsApiClient } from '../api/reports.api';
import { useReportsStore } from '../store/reports.store';
import { useReportExecutionPoll } from '../hooks/useReportExecutionPoll';
import { downloadReportArtifact, previewReportArtifact } from '../utils/downloadReportArtifact';
import { Eye, Download, ShieldCheck } from 'lucide-react';

export interface ReportExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportId: string;
  reportDefinition?: ReportDefinitionDTO | null;
  scope?: ReportScopeDTO;
  requestedBy?: string;
  onExportSuccess?: (execution: ReportExecutionResponse) => void;
  onExportError?: (error: any) => void;
}

const SHOW_JSON_EXPORT = false; // Manager requirement: Safely hide JSON export option without removing code

export const ReportExportModal: React.FC<ReportExportModalProps> = ({
  isOpen,
  onClose,
  reportId,
  reportDefinition,
  scope = {},
  requestedBy = 'SYSTEM',
  onExportSuccess,
  onExportError,
}) => {
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>(ReportFormat.PDF);
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [isPreviewing, setIsPreviewing] = useState<boolean>(false);

  const addExecution = useReportsStore((s) => s.addExecution);

  const { execution, isPolling, pollingError } = useReportExecutionPoll({
    executionId: activeExecutionId,
    enabled: Boolean(activeExecutionId),
    intervalMs: 1500,
  });

  // Format selection options based on report definition or default (JSON hidden safely)
  const rawSupportedFormats = reportDefinition?.supported_formats || [
    ReportFormat.PDF,
    ReportFormat.XLSX,
    ReportFormat.JSON,
  ];

  const supportedFormats = rawSupportedFormats.filter(
    (fmt) => SHOW_JSON_EXPORT || fmt !== ReportFormat.JSON
  );

  useEffect(() => {
    if (!isOpen) {
      setActiveExecutionId(null);
      setIsSubmitting(false);
      setSubmissionError(null);
      setIsDownloading(false);
      setIsPreviewing(false);
      setSelectedFormat(ReportFormat.PDF);
    }
  }, [isOpen]);

  const handleGenerate = async () => {
    if (isSubmitting || activeExecutionId) return;

    setIsSubmitting(true);
    setSubmissionError(null);

    try {
      const response = await reportsApiClient.generateReportAsync({
        report_id: reportId,
        format: selectedFormat,
        scope,
        requested_by: requestedBy,
      });

      addExecution(response);
      setActiveExecutionId(response.execution_id);
    } catch (err: any) {
      const errMsg = err.message || 'Failed to submit report execution request';
      setSubmissionError(errMsg);
      if (onExportError) onExportError(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownload = async () => {
    if (!activeExecutionId || isDownloading) return;
    setIsDownloading(true);
    try {
      await downloadReportArtifact({
        executionId: activeExecutionId,
        format: selectedFormat,
        reportId,
        onSuccess: () => {
          if (execution && onExportSuccess) onExportSuccess(execution);
        },
      });
    } catch (err: any) {
      if (onExportError) onExportError(err);
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePreview = async () => {
    if (!activeExecutionId || isPreviewing) return;
    setIsPreviewing(true);
    try {
      await previewReportArtifact({
        executionId: activeExecutionId,
        format: selectedFormat,
        reportId,
      });
    } catch (err: any) {
      if (onExportError) onExportError(err);
    } finally {
      setIsPreviewing(false);
    }
  };

  const formatOptions = supportedFormats.map((fmt) => ({
    value: fmt,
    label: fmt,
  }));

  const getStatusDisplay = () => {
    if (isSubmitting) return 'Submitting request...';
    if (!execution) return null;

    switch (execution.status) {
      case ReportStatus.QUEUED:
        return 'Report queued in background...';
      case ReportStatus.PROCESSING:
      case ReportStatus.RUNNING:
        return 'Generating report...';
      case ReportStatus.COMPLETED:
        return 'Report generation complete!';
      case ReportStatus.NO_DATA:
        return 'Report generated with no matching data.';
      case ReportStatus.FAILED:
        return `Report generation failed: ${execution.error_message || execution.error_code || 'Internal Error'}`;
      case ReportStatus.SCOPE_VALIDATION_FAILED:
        return `Scope Validation Failed: ${execution.error_message || 'Invalid parameters'}`;
      default:
        return `Status: ${execution.status}`;
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Export Report — ${reportDefinition?.title || reportId}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting || isDownloading || isPreviewing}>
            Close
          </Button>
          {!activeExecutionId && (
            <Button
              variant="primary"
              onClick={handleGenerate}
              disabled={isSubmitting}
              data-testid="export-modal-submit-button"
            >
              {isSubmitting ? 'Submitting...' : 'Generate & Export'}
            </Button>
          )}
          {execution?.status === ReportStatus.COMPLETED && (
            <div className="flex items-center gap-2">
              {selectedFormat === ReportFormat.PDF && (
                <Button
                  variant="secondary"
                  onClick={handlePreview}
                  disabled={isPreviewing || isDownloading}
                  data-testid="export-modal-preview-button"
                  className="inline-flex items-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5" />
                  {isPreviewing ? 'Opening Preview...' : 'Preview in Browser'}
                </Button>
              )}
              <Button
                variant="primary"
                onClick={handleDownload}
                disabled={isDownloading || isPreviewing}
                data-testid="export-modal-download-button"
                className="inline-flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                {isDownloading ? 'Downloading...' : 'Download File'}
              </Button>
            </div>
          )}
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div>
          <label className="text-xs text-slate-600 font-semibold mb-1.5 block">
            Export Format
          </label>
          <Select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value as ReportFormat)}
            options={formatOptions}
            disabled={isSubmitting || Boolean(activeExecutionId)}
            className="bg-white border-slate-200 text-slate-900"
            data-testid="export-modal-format-select"
          />
        </div>

        {/* Scope Context Information */}
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-800">
          <div className="font-bold text-slate-900 mb-1">Applied Scope</div>
          <div className="text-slate-600 font-medium">Plant: <strong className="text-slate-900">{scope.plant_id || 'ALL'}</strong></div>
          <div className="text-slate-600 font-medium">Customer: <strong className="text-slate-900">{scope.customer_id || 'ALL'}</strong></div>
          <div className="text-slate-600 font-medium">Date: <strong className="text-slate-900">{formatDisplayDate(scope.operation_date || '2026-08-05')}</strong></div>
        </div>

        {/* Status / Feedback Banner */}
        {(submissionError || pollingError) && (
          <div
            className="bg-rose-50 border border-rose-200 text-rose-700 p-2.5 rounded-lg text-xs font-semibold"
            data-testid="export-modal-error-banner"
          >
            {submissionError || pollingError}
          </div>
        )}

        {activeExecutionId && (
          <div
            className="bg-blue-50 border border-blue-200 text-blue-700 p-3 rounded-lg text-xs"
            data-testid="export-modal-status-banner"
          >
            <div className="font-bold">{getStatusDisplay()}</div>
            {isPolling && <div className="text-[11px] mt-1 text-blue-600 font-medium">Polling backend status...</div>}
          </div>
        )}

        {/* Direct Download Advisory Banner */}
        {execution?.status === ReportStatus.COMPLETED && (
          <div className="bg-amber-50/90 border border-amber-200/90 text-amber-900 p-3 rounded-lg text-xs space-y-1">
            <div className="font-bold flex items-center gap-1.5 text-amber-950">
              <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />
              Direct Download Advisory
            </div>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              If your browser asks to confirm or pauses this download (common when accessing via direct server IP before domain SSL is activated), select <strong>&quot;Keep&quot;</strong> to complete saving. Alternatively, use <strong>&quot;Preview in Browser&quot;</strong> to view the certified report immediately in a new tab.
            </p>
          </div>
        )}
      </div>
    </Modal>
  );
};
