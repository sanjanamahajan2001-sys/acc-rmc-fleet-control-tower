import { formatDisplayDateTime } from '../../../utils/date';
import React from 'react';
import { X, RefreshCw, User } from 'lucide-react';
import { ImportJobResponse } from '../types';
import { useERPJobsStore } from '../stores';

interface Props {
  job: ImportJobResponse | null;
  onClose: () => void;
}

export const ImportStatusDrawer: React.FC<Props> = ({ job, onClose }) => {
  const { cancelJob, retryJob } = useERPJobsStore();

  if (!job) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white border-l border-slate-200/90 shadow-2xl p-6 z-50 flex flex-col justify-between overflow-y-auto">
      <div className="space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900">{job.job_number}</h2>
            <p className="text-xs text-slate-500">Import Job Details &amp; Status</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-md bg-slate-50 border border-slate-200">
            <span className="text-xs font-semibold text-slate-600">Status</span>
            <span
              className={`px-2 py-0.5 text-xs font-bold font-mono rounded border ${
                job.status === 'COMPLETED'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                  : job.status === 'FAILED'
                  ? 'bg-rose-50 border-rose-200 text-rose-700'
                  : 'bg-blue-50 border-blue-200 text-blue-700'
              }`}
            >
              {job.status}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Workbook File</span>
              <span className="text-slate-800 font-mono font-bold text-xs">{job.file_name}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Uploaded By</span>
              <span className="text-slate-800 font-sans font-bold text-xs flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-blue-600" />
                <span>{job.uploaded_by && job.uploaded_by !== 'Sanjana Mahajan' ? job.uploaded_by : 'admin'}</span>
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Dataset State</span>
              {job.is_reset ? (
                <span className="text-amber-800 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-bold border border-amber-300">
                  Reset / Archived
                </span>
              ) : (
                <span className="text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded text-[11px] font-bold border border-emerald-300">
                  Active Operational Dataset
                </span>
              )}
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">SHA-256 Checksum</span>
              <span className="text-slate-600 font-mono text-[11px] truncate max-w-[180px]">
                {job.file_hash}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Total Rows</span>
              <span className="text-slate-800 font-bold">{job.total_rows}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Processed Rows</span>
              <span className="text-emerald-700 font-bold">{job.processed_rows}</span>
            </div>
            {job.inserted_rows !== undefined && job.inserted_rows !== null && (
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-semibold">New Dispatches</span>
                <span className="text-blue-700 font-mono font-bold text-xs">{job.inserted_rows}</span>
              </div>
            )}
            {job.updated_rows !== undefined && job.updated_rows !== null && (
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-semibold">Updated (Deduplicated)</span>
                <span className="text-amber-700 font-mono font-bold text-xs">{job.updated_rows}</span>
              </div>
            )}
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Validation Errors</span>
              <span className={`font-bold ${job.error_count > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>{job.error_count}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Created At</span>
              <span className="text-slate-600 font-medium">{formatDisplayDateTime(job.created_at, true)}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-500 font-semibold">Completed At</span>
              <span className="text-emerald-700 font-medium">
                {job.completed_at
                  ? formatDisplayDateTime(job.completed_at, true)
                  : job.status === 'COMPLETED'
                  ? formatDisplayDateTime(job.updated_at, true)
                  : 'In Progress'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2.5 pt-5 border-t border-slate-100">
        <button
          type="button"
          onClick={() => cancelJob(job.job_number)}
          className="flex-1 py-2 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-bold transition-colors shadow-xs"
        >
          Cancel Job
        </button>
        <button
          type="button"
          onClick={() => retryJob(job.job_number)}
          className="flex-1 py-2 rounded-md bg-blue-700 text-white hover:bg-blue-800 text-xs font-bold transition-colors flex items-center justify-center gap-1.5 shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Job
        </button>
      </div>
    </div>
  );
};
