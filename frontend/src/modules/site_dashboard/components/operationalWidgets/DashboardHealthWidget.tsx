import React from 'react';

export interface DashboardHealthData {
  dashboard_status: 'GOOD' | 'WARNING' | 'CRITICAL';
  last_erp_import: string;
  backend_processing_time_ms: number;
  calculation_duration_ms: number;
  canonical_snapshot_version: string;
  total_records_evaluated: number;
  import_completeness_pct: number;
  database_freshness: string;
  canonical_sync_status: 'SYNCHRONIZED' | 'LAGGING' | 'OUT_OF_SYNC';
}

interface DashboardHealthWidgetProps {
  health: DashboardHealthData | null;
}

export const DashboardHealthWidget: React.FC<DashboardHealthWidgetProps> = ({ health }) => {
  if (!health) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 italic border border-slate-800/80 rounded-xl bg-slate-950/60">
        No dashboard metrics available.
      </div>
    );
  }

  const badgeColors: Record<string, string> = {
    GOOD: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    WARNING: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800/90 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          DASHBOARD OPERATIONAL HEALTH & DATA FRESHNESS
        </h3>
        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold border ${badgeColors[health.dashboard_status]}`}>
          {health.dashboard_status} OPERATIONAL
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Last ERP Import</span>
          <p className="text-slate-200 font-mono font-bold">{health.last_erp_import}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Backend Processing Time</span>
          <p className="text-emerald-400 font-mono font-bold">{health.backend_processing_time_ms} ms</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Snapshot Version</span>
          <p className="text-indigo-400 font-mono font-bold">{health.canonical_snapshot_version}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Records Evaluated</span>
          <p className="text-slate-100 font-mono font-bold">{health.total_records_evaluated.toLocaleString()}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Import Completeness</span>
          <p className="text-emerald-400 font-mono font-bold">{health.import_completeness_pct}%</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Database Freshness</span>
          <p className="text-slate-300 font-mono font-bold">{health.database_freshness}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Canonical Sync</span>
          <p className="text-emerald-400 font-mono font-bold">{health.canonical_sync_status}</p>
        </div>
        <div className="space-y-0.5">
          <span className="text-[10px] text-slate-400 font-medium">Calculation Engine</span>
          <p className="text-indigo-300 font-mono font-bold">{health.calculation_duration_ms} ms</p>
        </div>
      </div>
    </div>
  );
};
