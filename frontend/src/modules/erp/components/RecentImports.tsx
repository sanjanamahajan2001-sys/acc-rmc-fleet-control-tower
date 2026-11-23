import { formatDisplayDate } from '../../../utils/date';
import React, { useState, useMemo } from 'react';
import {
  Eye,
  RotateCcw,
  XCircle,
  User,
  ChevronLeft,
  ChevronRight,
  Archive,
  CheckCircle2,
  History,
  Undo2,
  AlertTriangle,
  X,
  Loader2,
} from 'lucide-react';
import { IconExcelSpreadsheet } from '../../../components/icons/LinealColorIcons';
import { useERPJobsStore, useERPStatisticsStore, useERPNotificationStore } from '../stores';
import { ImportJobResponse } from '../types';
import { usePermissions } from '../../../hooks/usePermissions';

interface Props {
  onSelectJob: (job: ImportJobResponse) => void;
  onRevertJob?: (job: ImportJobResponse) => void;
}

type TabType = 'active' | 'archived' | 'all';

export const RecentImports: React.FC<Props> = ({ onSelectJob, onRevertJob }) => {
  const { jobs, loading, cancelJob, retryJob, revertDataset } = useERPJobsStore();
  const fetchStatistics = useERPStatisticsStore((s) => s.fetchStatistics);
  const fetchAuditLogs = useERPStatisticsStore((s) => s.fetchAuditLogs);
  const addNotification = useERPNotificationStore((s) => s.addNotification);
  const { canEdit } = usePermissions();

  const [currentTab, setCurrentTab] = useState<TabType>('active');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const PAGE_SIZE = 10;

  const [revertingJob, setRevertingJob] = useState<ImportJobResponse | null>(null);
  const [isReverting, setIsReverting] = useState(false);

  // Split jobs: Active dataset contains ONLY non-reset files belonging to the current active operational period
  const activeJobs = useMemo(
    () => jobs.filter((j) => !j.is_reset && (j.is_active_dataset !== undefined ? j.is_active_dataset : true)),
    [jobs]
  );
  const archivedJobs = useMemo(
    () => jobs.filter((j) => j.is_reset || (j.is_active_dataset !== undefined && !j.is_active_dataset)),
    [jobs]
  );

  // Determine current filtered dataset
  const filteredJobs = useMemo(() => {
    if (currentTab === 'active') return activeJobs;
    if (currentTab === 'archived') return archivedJobs;
    return jobs;
  }, [currentTab, activeJobs, archivedJobs, jobs]);

  // Pagination calculations (10 items per page)
  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / PAGE_SIZE));
  const validPage = Math.min(currentPage, totalPages);
  const startIndex = (validPage - 1) * PAGE_SIZE;
  const paginatedJobs = filteredJobs.slice(startIndex, startIndex + PAGE_SIZE);

  const handleTabChange = (tab: TabType) => {
    setCurrentTab(tab);
    setCurrentPage(1);
  };

  const handleConfirmRevert = async () => {
    if (!revertingJob) return;
    if (onRevertJob) {
      onRevertJob(revertingJob);
      setRevertingJob(null);
      return;
    }
    setIsReverting(true);
    try {
      await revertDataset({
        period_key: revertingJob.dataset_period || undefined,
        job_number: revertingJob.job_number,
      });
      await Promise.all([fetchStatistics(), fetchAuditLogs()]);
      addNotification(
        'success',
        `Platform successfully reverted to ${revertingJob.dataset_period || revertingJob.file_name}. All dashboards updated.`
      );
      setRevertingJob(null);
    } catch (err: any) {
      addNotification('error', err.message || 'Dataset revert failed.');
    } finally {
      setIsReverting(false);
    }
  };

  return (
    <div className="p-5 rounded-lg border border-slate-200/90 bg-white space-y-4 shadow-xs font-sans">
      {/* Header and Filter Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <IconExcelSpreadsheet className="w-4 h-4 shrink-0" />
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Ingestion Jobs &amp; Dataset History
            </h3>
            <p className="text-[11px] text-slate-500 font-sans">
              10 records per page • Clear active period vs. prior &amp; reset archive segmentation
            </p>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-sans">
          <button
            type="button"
            onClick={() => handleTabChange('active')}
            className={`px-3 py-1 rounded-md font-bold transition-all flex items-center gap-1.5 ${
              currentTab === 'active'
                ? 'bg-white text-emerald-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Active Dataset</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                currentTab === 'active' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
              }`}
            >
              {activeJobs.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => handleTabChange('archived')}
            className={`px-3 py-1 rounded-md font-bold transition-all flex items-center gap-1.5 ${
              currentTab === 'archived'
                ? 'bg-white text-amber-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Archive className="w-3.5 h-3.5 text-amber-600" />
            <span>Archived</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                currentTab === 'archived' ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-600'
              }`}
            >
              {archivedJobs.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => handleTabChange('all')}
            className={`px-3 py-1 rounded-md font-bold transition-all flex items-center gap-1.5 ${
              currentTab === 'all'
                ? 'bg-white text-blue-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span>All History</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                currentTab === 'all' ? 'bg-blue-100 text-blue-800' : 'bg-slate-200 text-slate-600'
              }`}
            >
              {jobs.length}
            </span>
          </button>
        </div>
      </div>

      {/* Dataset Revert Mode Informational Banner */}
      {currentTab === 'archived' && (
        <div className="flex items-start gap-3 p-3.5 rounded-lg bg-amber-50/80 border border-amber-200 text-amber-950 text-xs">
          <Undo2 className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold text-amber-950">
              Dataset Revert &amp; Resume Mode
            </p>
            <p className="text-amber-800 leading-relaxed text-[11px]">
              Archived historical and reset datasets are preserved here with full lineage. Administrators can click <strong className="font-bold text-amber-950">Revert</strong> on any archived dataset to resume operations from that period. Reverting reconstitutes operational dispatches, trip drum telemetry, ML predictions, and synchronizes all platform dashboards (including Operational Date and Dataset ID).
            </p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="border border-slate-200 rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                <th className="py-2.5 px-3">Job Number</th>
                <th className="py-2.5 px-3">Workbook</th>
                <th className="py-2.5 px-3">Dataset State</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Uploaded By</th>
                <th className="py-2.5 px-3">Processed / Total</th>
                <th className="py-2.5 px-3">Errors</th>
                <th className="py-2.5 px-3">Completed At</th>
                <th className="py-2.5 px-3 text-right font-sans">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center font-bold text-slate-500 font-sans">
                    Loading import jobs...
                  </td>
                </tr>
              ) : paginatedJobs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center font-medium text-slate-500 font-sans">
                    {currentTab === 'active' ? (
                      <div className="space-y-1">
                        <p className="font-bold text-slate-700">No active post-reset imports.</p>
                        <p className="text-xs text-slate-500">
                          Operational tables were reset. Upload a workbook above to ingest a new active dataset, or switch to the &quot;Archived (Pre-Reset)&quot; tab to inspect historical files.
                        </p>
                      </div>
                    ) : currentTab === 'archived' ? (
                      <p>No archived pre-reset files found.</p>
                    ) : (
                      <p>No import jobs found. Upload a workbook above to start ingestion.</p>
                    )}
                  </td>
                </tr>
              ) : (
                paginatedJobs.map((job, idx) => (
                  <tr
                    key={job.id}
                    className={`hover:bg-slate-50/80 transition-colors ${
                      idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'
                    }`}
                  >
                    <td className="py-2.5 px-3 font-bold text-blue-700">{job.job_number}</td>
                    <td className="py-2.5 px-3 font-bold font-sans text-slate-900">
                      <div>{job.file_name}</div>
                      {job.file_type && (
                        <span
                          className={`inline-block text-[10px] font-semibold px-1.5 py-0.2 rounded mt-0.5 border ${
                            job.file_type === 'Trip Drum Telemetry'
                              ? 'bg-purple-50 text-purple-700 border-purple-200'
                              : 'bg-blue-50 text-blue-700 border-blue-200'
                          }`}
                        >
                          {job.file_type}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      {job.is_reset ? (
                        <div className="space-y-0.5">
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-bold border text-[10px] bg-amber-50 border-amber-300 text-amber-800"
                            title="Archived dataset."
                          >
                            <Archive className="w-3 h-3 text-amber-600 shrink-0" />
                            <span>Archived</span>
                          </span>
                          {job.dataset_period && (
                            <p className="text-[10px] text-slate-400 font-medium">{job.dataset_period}</p>
                          )}
                        </div>
                      ) : job.is_active_dataset ? (
                        <div className="space-y-0.5">
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-bold border text-[10px] bg-emerald-50 border-emerald-300 text-emerald-800"
                            title="Currently active in PostgreSQL operational database."
                          >
                            <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                            <span>Active Dataset</span>
                          </span>
                          {job.dataset_period && (
                            <p className="text-[10px] text-emerald-700 font-semibold">{job.dataset_period}</p>
                          )}
                        </div>
                      ) : (
                        <div className="space-y-0.5">
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-bold border text-[10px] bg-amber-50 border-amber-300 text-amber-800"
                            title="Archived dataset."
                          >
                            <Archive className="w-3 h-3 text-amber-600 shrink-0" />
                            <span>Archived</span>
                          </span>
                          {job.dataset_period && (
                            <p className="text-[10px] text-slate-500 font-medium">{job.dataset_period}</p>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded font-bold border text-[10px] ${
                          job.status === 'COMPLETED' || job.status === 'UPLOADED'
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                            : job.status === 'FAILED'
                            ? 'bg-rose-50 border-rose-200 text-rose-700'
                            : 'bg-blue-50 border-blue-200 text-blue-700'
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-100 text-slate-800 text-[11px] font-semibold border border-slate-200 shadow-2xs">
                        <User className="w-3 h-3 text-blue-600 shrink-0" />
                        <span className="truncate max-w-[120px]">
                          {job.uploaded_by && job.uploaded_by !== 'Sanjana Mahajan' ? job.uploaded_by : 'admin'}
                        </span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-600">
                      {job.processed_rows} / {job.total_rows}
                    </td>
                    <td
                      className={`py-2.5 px-3 font-bold ${
                        job.error_count > 0 ? 'text-rose-700' : 'text-emerald-700'
                      }`}
                    >
                      {job.error_count}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-600 whitespace-nowrap">
                      {job.completed_at || (job.status === 'COMPLETED' ? job.updated_at : null) ? (
                        <div className="flex flex-col">
                          <span className="font-mono text-xs font-semibold text-slate-800">
                            {formatDisplayDate(job.completed_at || job.updated_at)}
                          </span>
                          <span className="font-mono text-[11px] text-slate-400">
                            {new Date(job.completed_at || job.updated_at).toLocaleTimeString()}
                          </span>
                        </div>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-1.5 font-sans whitespace-nowrap">
                      {/* Revert Button for Archived / Prior datasets */}
                      {canEdit && (job.is_reset || !job.is_active_dataset) && job.status === 'COMPLETED' && (
                        <button
                          type="button"
                          onClick={() => setRevertingJob(job)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 font-bold text-[11px] transition-all shadow-2xs hover:shadow-xs active:scale-95"
                          title="Revert platform to this dataset period"
                        >
                          <Undo2 className="w-3.5 h-3.5 text-amber-700" />
                          <span>Revert</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => onSelectJob(job)}
                        className="p-1 rounded border border-slate-200 bg-white text-blue-700 hover:bg-blue-50 transition-colors shadow-2xs"
                        title="Inspect Job"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => retryJob(job.job_number)}
                        className="p-1 rounded border border-slate-200 bg-white text-emerald-700 hover:bg-emerald-50 transition-colors shadow-2xs"
                        title="Retry Job"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => cancelJob(job.job_number)}
                        className="p-1 rounded border border-slate-200 bg-white text-rose-700 hover:bg-rose-50 transition-colors shadow-2xs"
                        title="Cancel Job"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination Controls (10 items per page) */}
      {filteredJobs.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 px-1 text-xs text-slate-600 font-sans">
          <div>
            Showing <span className="font-bold text-slate-900">{startIndex + 1}</span> to{' '}
            <span className="font-bold text-slate-900">
              {Math.min(startIndex + PAGE_SIZE, filteredJobs.length)}
            </span>{' '}
            of <span className="font-bold text-slate-900">{filteredJobs.length}</span> files
            <span className="text-slate-400 ml-2">
              (Page {validPage} of {totalPages})
            </span>
          </div>

          <div className="flex items-center gap-1.5 self-end sm:self-auto">
            <button
              type="button"
              disabled={validPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="px-2.5 py-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium flex items-center gap-1 transition-colors shadow-2xs"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
            <span className="px-2 py-1 text-slate-700 font-semibold text-xs">
              {validPage} / {totalPages}
            </span>
            <button
              type="button"
              disabled={validPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="px-2.5 py-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium flex items-center gap-1 transition-colors shadow-2xs"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Revert Confirmation Modal */}
      {revertingJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-2xs p-4 animate-in fade-in duration-200 font-sans">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-amber-50/50">
              <div className="flex items-center gap-2 text-amber-800">
                <div className="p-1.5 rounded-lg bg-amber-100 text-amber-700">
                  <Undo2 className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-slate-900">Confirm Dataset Revert &amp; Resume</h4>
                  <p className="text-[11px] text-slate-500 font-mono">Job: {revertingJob.job_number}</p>
                </div>
              </div>
              <button
                type="button"
                disabled={isReverting}
                onClick={() => setRevertingJob(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors disabled:opacity-50"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 space-y-4 text-xs text-slate-600">
              <div className="p-3 bg-amber-50/90 rounded-lg border border-amber-200 text-amber-950 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-amber-950">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Operational Rollback Notice</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  You are about to revert the platform to historical dataset{' '}
                  <strong className="font-bold text-amber-950">
                    {revertingJob.dataset_period || revertingJob.file_name}
                  </strong>.
                </p>
              </div>

              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-2 font-mono text-[11px]">
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500 font-sans">Target Dataset Period:</span>
                  <span className="font-bold text-slate-800">{revertingJob.dataset_period || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500 font-sans">Workbook / File:</span>
                  <span className="font-bold text-slate-800 truncate max-w-[260px]">{revertingJob.file_name}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500 font-sans">File Classification:</span>
                  <span className="font-bold text-blue-700">{revertingJob.file_type || 'ERP Dispatches'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500 font-sans">Recorded Rows:</span>
                  <span className="font-bold text-emerald-700">{revertingJob.processed_rows} rows</span>
                </div>
              </div>

              <div className="text-[11px] text-slate-600 space-y-1.5 font-sans">
                <p className="font-bold text-slate-800">What happens during Revert:</p>
                <ul className="list-disc list-inside space-y-1 text-slate-600 pl-1">
                  <li>Reverts the complete dataset batch (both ERP Dispatches and Trip Drum Telemetry files together)</li>
                  <li>Transactionally resets active operational tables in PostgreSQL</li>
                  <li>Re-ingests and correlates telemetry with dispatches</li>
                  <li>Regenerates ML predictions, recommendation exposure, and alert center events</li>
                  <li>Synchronizes all platform dashboards with the reverted Operational Date and Dataset ID</li>
                </ul>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2.5">
              <button
                type="button"
                disabled={isReverting}
                onClick={() => setRevertingJob(null)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-bold hover:bg-slate-100 transition-colors disabled:opacity-50 text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isReverting}
                onClick={handleConfirmRevert}
                className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold transition-all shadow-xs disabled:opacity-50 flex items-center gap-1.5 text-xs"
              >
                {isReverting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Reverting &amp; Reprocessing...</span>
                  </>
                ) : (
                  <>
                    <Undo2 className="w-3.5 h-3.5" />
                    <span>Confirm Revert &amp; Resume</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
