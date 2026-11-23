import { formatDisplayDate, formatDisplayDateTime } from '../../../utils/date';
import React from 'react';

export interface DatasetInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  datasetInfo: {
    operational_date?: string;
    dataset_id?: string;
    import_timestamp?: string;
    dataset_status?: string;
    total_dispatches?: number;
  } | null;
}

export const DatasetInfoModal: React.FC<DatasetInfoModalProps> = ({
  isOpen,
  onClose,
  datasetInfo,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Dataset Technical Metadata
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-lg font-bold p-1 rounded"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div className="flex justify-between py-1.5 border-b border-slate-800/60">
            <span className="text-slate-400">Operational Date:</span>
            <span className="font-mono text-indigo-300 font-semibold">
              {formatDisplayDate(datasetInfo?.operational_date)}
            </span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-800/60">
            <span className="text-slate-400">Dataset Scope ID:</span>
            <span className="font-mono text-slate-200">{datasetInfo?.dataset_id || 'N/A'}</span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-800/60">
            <span className="text-slate-400">Dataset Status:</span>
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/30">
              {datasetInfo?.dataset_status || 'ACTIVE'}
            </span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-slate-800/60">
            <span className="text-slate-400">Total Canonical Dispatches:</span>
            <span className="font-mono text-slate-200 font-bold">
              {datasetInfo?.total_dispatches?.toLocaleString() || '0'}
            </span>
          </div>

          <div className="flex justify-between py-1.5">
            <span className="text-slate-400">Last Synchronized:</span>
            <span className="font-mono text-slate-300">
              {datasetInfo?.import_timestamp
                ? formatDisplayDateTime(datasetInfo.import_timestamp)
                : 'Just Now'}
            </span>
          </div>
        </div>

        <div className="pt-2 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
