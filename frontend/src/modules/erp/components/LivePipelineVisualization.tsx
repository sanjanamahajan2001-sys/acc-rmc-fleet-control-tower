import React from 'react';
import { IconOperationalPulse, IconEfficiencyTimer, IconCycleStopwatch, IconPredictiveRadar, IconServerStorage } from '../../../components/icons/LinealColorIcons';
import { useERPProgressStore } from '../stores';

export const LivePipelineVisualization: React.FC = () => {
  const snapshot = useERPProgressStore((s) => s.snapshot);
  const isStreaming = useERPProgressStore((s) => s.isStreaming);

  if (!isStreaming && !snapshot) {
    return (
      <div className="p-6 rounded-lg border border-slate-200/90 bg-white text-center shadow-xs text-slate-500">
        <IconOperationalPulse className="w-8 h-8 mx-auto mb-2" />
        <p className="text-xs font-medium">No active import pipeline. Upload a workbook to stream live metrics.</p>
      </div>
    );
  }

  return (
    <div className="p-5 rounded-lg border border-slate-200/90 bg-white space-y-5 shadow-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <IconOperationalPulse className="w-6 h-6 shrink-0" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">Live Ingestion Telemetry</h3>
            <p className="text-xs font-medium font-mono text-slate-500">
              Job: {snapshot?.job_id || 'Connecting...'} • Worker: {snapshot?.worker_id || 'worker-01'}
            </p>
          </div>
        </div>

        <span className="px-2.5 py-0.5 text-xs font-bold font-mono rounded-full border bg-blue-50 text-blue-700 border-blue-200">
          {snapshot?.stage || 'STREAMING'}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="font-medium text-slate-500">Ingestion Progress</span>
          <span className="font-bold font-mono text-blue-700">{snapshot?.percentage || 0}%</span>
        </div>
        <div className="w-full h-2.5 rounded-full overflow-hidden border border-slate-200 bg-slate-100">
          <div
            className="h-full transition-all duration-300 ease-out bg-blue-700"
            style={{ width: `${snapshot?.percentage || 0}%` }}
          />
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded-md border border-slate-200 bg-slate-50/60">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 mb-1">
            <IconEfficiencyTimer className="w-4 h-4" />
            Throughput
          </div>
          <p className="text-base font-bold font-mono text-slate-900">
            {snapshot?.throughput_rows_per_sec || 0} <span className="text-xs font-medium font-sans text-slate-500">rows/sec</span>
          </p>
        </div>

        <div className="p-3 rounded-md border border-slate-200 bg-slate-50/60">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 mb-1">
            <IconCycleStopwatch className="w-4 h-4" />
            Elapsed / ETA
          </div>
          <p className="text-base font-bold font-mono text-slate-900">
            {snapshot?.elapsed_seconds || 0}s <span className="text-xs font-medium font-sans text-slate-500">/ {snapshot?.eta_seconds || 0}s</span>
          </p>
        </div>

        <div className="p-3 rounded-md border border-slate-200 bg-slate-50/60">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 mb-1">
            <IconPredictiveRadar className="w-4 h-4" />
            Memory Usage
          </div>
          <p className="text-base font-bold font-mono text-slate-900">
            {snapshot?.memory_mb || 0} <span className="text-xs font-medium font-sans text-slate-500">MB</span>
          </p>
        </div>

        <div className="p-3 rounded-md border border-slate-200 bg-slate-50/60">
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 mb-1">
            <IconServerStorage className="w-4 h-4" />
            Rows Ingested
          </div>
          <p className="text-base font-bold font-mono text-slate-900">
            {snapshot?.rows_processed || 0} <span className="text-xs font-medium font-sans text-slate-500">/ {snapshot?.rows_total || 0}</span>
          </p>
        </div>
      </div>
    </div>
  );
};
