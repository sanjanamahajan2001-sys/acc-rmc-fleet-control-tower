import { formatDisplayDate, formatDisplayDateTime } from '../../../utils/date';
import React, { useState, useMemo } from 'react';
import { ReportExecutionResponse, ReportStatus, ReportFormat } from '../types/report.types';
import { StatusChip } from '../../../components/display/StatusChip';
import { downloadReportArtifact, previewReportArtifact } from '../utils/downloadReportArtifact';
import { Download, RefreshCw, AlertCircle, Info, Search, X, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { IconCycleStopwatch } from '../../../components/icons/LinealColorIcons';

export interface ReportExecutionHistoryTableProps {
  executions: ReportExecutionResponse[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

const SHOW_JSON_DOWNLOAD = false; // Manager requirement: Safely hide JSON download without removing code

export const ReportExecutionHistoryTable: React.FC<ReportExecutionHistoryTableProps> = ({
  executions,
  isLoading = false,
  error = null,
  onRefresh,
}) => {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<ReportExecutionResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  const handlePreview = async (exec: ReportExecutionResponse) => {
    if (previewingId || exec.status !== ReportStatus.COMPLETED) return;
    setPreviewingId(exec.execution_id);
    try {
      await previewReportArtifact({
        executionId: exec.execution_id,
        format: exec.format,
        reportId: exec.report_id,
      });
    } catch (err) {
      // Error handled inside previewer
    } finally {
      setPreviewingId(null);
    }
  };

  const handleDownload = async (exec: ReportExecutionResponse) => {
    if (downloadingId || exec.status !== ReportStatus.COMPLETED) return;
    setDownloadingId(exec.execution_id);
    try {
      await downloadReportArtifact({
        executionId: exec.execution_id,
        format: exec.format,
        reportId: exec.report_id,
      });
    } catch (err) {
      // Error handled inside downloader
    } finally {
      setDownloadingId(null);
    }
  };

  const getStatusChip = (status: ReportStatus) => {
    switch (status) {
      case ReportStatus.COMPLETED:
        return <StatusChip label="COMPLETED" status="success" />;
      case ReportStatus.NO_DATA:
        return <StatusChip label="NO_DATA" status="info" />;
      case ReportStatus.QUEUED:
        return <StatusChip label="QUEUED" status="warning" />;
      case ReportStatus.PROCESSING:
      case ReportStatus.RUNNING:
        return <StatusChip label="PROCESSING" status="warning" />;
      case ReportStatus.FAILED:
      case ReportStatus.SCOPE_VALIDATION_FAILED:
        return <StatusChip label="FAILED" status="danger" />;
      case ReportStatus.PURGED:
        return <StatusChip label="PURGED" status="muted" />;
      default:
        return <StatusChip label={status} status="info" />;
    }
  };

  const filteredExecutions = useMemo(() => {
    if (!searchQuery.trim()) return executions;
    const q = searchQuery.toLowerCase().trim();
    return executions.filter(
      (exec) =>
        exec.execution_id?.toLowerCase().includes(q) ||
        exec.report_id?.toLowerCase().includes(q) ||
        exec.format?.toLowerCase().includes(q) ||
        exec.status?.toLowerCase().includes(q) ||
        exec.requested_by?.toLowerCase().includes(q) ||
        exec.scope_fingerprint?.toLowerCase().includes(q)
    );
  }, [executions, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredExecutions.length / pageSize));
  const paginatedExecutions = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredExecutions.slice(start, start + pageSize);
  }, [filteredExecutions, currentPage, pageSize]);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <IconCycleStopwatch className="w-5 h-5 inline-block" />
            Execution Run History &amp; Audit Log
          </h3>
          <p className="text-xs text-slate-500 font-medium">
            Immutable log of previously triggered reports with scope hash fingerprints
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search executions..."
              className="pl-8 pr-7 py-1.5 text-xs rounded-md border border-slate-200 bg-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700 w-48 sm:w-56 shadow-2xs"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                title="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <span className="text-[11px] font-mono tabular-nums text-slate-500 font-semibold px-2 py-1 bg-slate-50 border border-slate-200 rounded-md">
            {searchQuery
              ? `Matches: ${filteredExecutions.length} of ${executions.length}`
              : `Total: ${executions.length}`}
          </span>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors cursor-pointer"
              data-testid="refresh-executions-btn"
            >
              <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
              Refresh History
            </button>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div
          className="p-3 rounded-md bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold flex items-center gap-2"
          data-testid="history-error-banner"
        >
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && executions.length === 0 ? (
        <div className="p-8 text-center text-blue-700 text-xs font-semibold" data-testid="history-loading-state">
          Loading execution history...
        </div>
      ) : executions.length === 0 ? (
        <div
          className="p-8 text-center text-slate-500 text-xs font-medium bg-slate-50/50 rounded-md border border-dashed border-slate-200"
          data-testid="history-empty-state"
        >
          No historical report executions found.
        </div>
      ) : filteredExecutions.length === 0 ? (
        <div className="p-8 text-center text-slate-500 text-xs italic bg-slate-50/50 rounded-md border border-slate-200">
          No executions match query &quot;{searchQuery}&quot;.
        </div>
      ) : (
        <div className="border border-slate-200 rounded-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs text-left">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-[10px] uppercase font-bold tracking-wider">
                  <th className="py-2.5 px-3.5">Execution ID</th>
                  <th className="py-2.5 px-3.5">Report ID</th>
                  <th className="py-2.5 px-3.5">Format</th>
                  <th className="py-2.5 px-3.5">Status</th>
                  <th className="py-2.5 px-3.5">Records</th>
                  <th className="py-2.5 px-3.5">Requested At</th>
                  <th className="py-2.5 px-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedExecutions.map((exec, idx) => (
                  <tr
                    key={exec.execution_id}
                    className={`hover:bg-slate-50/80 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}
                    data-testid={'execution-row-' + exec.execution_id}
                  >
                    <td className="py-2.5 px-3.5 font-mono text-[11px] text-slate-600 font-semibold">
                      {exec.execution_id}
                    </td>
                    <td className="py-2.5 px-3.5 font-bold text-slate-900">{exec.report_id}</td>
                    <td className="py-2.5 px-3.5 font-semibold text-slate-600">{exec.format}</td>
                    <td className="py-2.5 px-3.5">{getStatusChip(exec.status)}</td>
                    <td className="py-2.5 px-3.5 font-semibold text-slate-600">{exec.record_count ?? 0}</td>
                    <td className="py-2.5 px-3.5 text-slate-500 font-medium">
                      {exec.requested_at ? formatDisplayDateTime(exec.requested_at) : 'N/A'}
                    </td>

                    <td className="py-2.5 px-3.5 text-right">
                      <div className="flex gap-2 justify-end items-center">
                        <button
                          onClick={() => setSelectedExecution(exec)}
                          className="text-blue-700 hover:text-blue-800 font-bold text-xs inline-flex items-center gap-1 cursor-pointer"
                          data-testid={'scope-btn-' + exec.execution_id}
                        >
                          <Info size={13} /> Scope
                        </button>
                        {exec.status === ReportStatus.COMPLETED &&
                          (SHOW_JSON_DOWNLOAD || exec.format !== ReportFormat.JSON) && (
                            <>
                              {exec.format.toLowerCase() === 'pdf' && (
                                <button
                                  disabled={previewingId === exec.execution_id}
                                  onClick={() => handlePreview(exec)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                                  title="Open PDF directly in browser"
                                  data-testid={'preview-btn-' + exec.execution_id}
                                >
                                  <Eye size={12} />
                                  {previewingId === exec.execution_id ? 'Opening...' : 'Preview'}
                                </button>
                              )}
                              <button
                                disabled={downloadingId === exec.execution_id}
                                onClick={() => handleDownload(exec)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 text-xs font-bold transition-colors disabled:opacity-50 cursor-pointer"
                                data-testid={'download-btn-' + exec.execution_id}
                              >
                                <Download size={11} />
                                {downloadingId === exec.execution_id ? 'Downloading...' : 'Download'}
                              </button>
                            </>
                          )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 10-Row Pagination Bar */}
          {totalPages > 1 && (
            <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs text-slate-600">
              <div>
                Showing <strong className="text-slate-900 font-mono">{paginatedExecutions.length}</strong> of{' '}
                <strong className="text-slate-900 font-mono">{filteredExecutions.length}</strong> executions
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                  title="Previous Page"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <span className="font-mono text-[11px] px-1.5">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                  title="Next Page"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Execution Scope Detail View Modal */}
      {selectedExecution && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedExecution(null)}
          data-testid="execution-scope-modal"
        >
          <div
            className="w-full max-w-md p-5 bg-white rounded-lg border border-slate-200 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center pb-2.5 mb-3 border-b border-slate-100">
              <h4 className="text-sm font-bold text-slate-900">
                Immutable Execution Scope Details
              </h4>
              <button
                onClick={() => setSelectedExecution(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>
            <div className="text-xs text-slate-700 flex flex-col gap-2">
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Execution ID:</strong> <span className="font-mono font-semibold text-slate-800">{selectedExecution.execution_id}</span></div>
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Report ID:</strong> <span className="font-bold text-slate-900">{selectedExecution.report_id}</span></div>
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Requested By:</strong> <span className="font-semibold text-slate-800">{selectedExecution.requested_by}</span></div>
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Plant ID:</strong> <span className="font-semibold text-slate-800">{String(selectedExecution.effective_scope?.plant_id || selectedExecution.requested_scope?.plant_id || 'ALL')}</span></div>
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Customer ID:</strong> <span className="font-semibold text-slate-800">{String(selectedExecution.effective_scope?.customer_id || selectedExecution.requested_scope?.customer_id || 'ALL')}</span></div>
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Operation Date:</strong> <span className="font-semibold text-slate-800">{formatDisplayDate((selectedExecution.effective_scope?.operation_date || selectedExecution.requested_scope?.operation_date) as string)}</span></div>
              <div className="flex justify-between"><strong className="text-slate-500 font-semibold">Scope Fingerprint:</strong> <span className="font-mono text-[11px] text-blue-700 font-semibold">{selectedExecution.scope_fingerprint}</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
