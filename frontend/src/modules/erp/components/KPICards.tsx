import React from 'react';
import { CheckCircle, AlertTriangle, Gauge, Layers, ShieldCheck } from 'lucide-react';
import { IconDatasetDatabase, IconCalendarCheckmark, IconCriticalAlert, IconOverlapHeatmap, IconEfficiencyTimer, IconShieldSecure } from '../../../components/icons/LinealColorIcons';
import { useERPStatisticsStore, useERPJobsStore } from '../stores';

export const KPICards: React.FC = () => {
  const stats = useERPStatisticsStore((s) => s.statistics);
  const totalJobs = useERPJobsStore((s) => s.totalRecords);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <div className="p-4 rounded-lg border border-slate-200/90 bg-white space-y-1 shadow-xs">
        <div className="flex items-center justify-between text-slate-500">
          <span className="text-[11px] font-bold uppercase tracking-wider">Total Imports</span>
          <IconDatasetDatabase className="w-4 h-4" />
        </div>
        <div className="flex items-baseline gap-2">
          <p className="text-2xl font-bold font-mono text-slate-900">{totalJobs || stats?.total_imports || 0}</p>
          {(stats?.archived_imports ?? 0) > 0 && (
            <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
              {stats?.active_imports ?? 0} active / {stats?.archived_imports} archived
            </span>
          )}
        </div>
      </div>

      <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50 space-y-1 shadow-xs">
        <div className="flex items-center justify-between text-emerald-700">
          <span className="text-[11px] font-bold uppercase tracking-wider">Completed</span>
          <IconCalendarCheckmark className="w-4 h-4" />
        </div>
        <p className="text-2xl font-bold font-mono text-emerald-700">{stats?.completed_imports || 0}</p>
      </div>

      <div className="p-4 rounded-lg border border-rose-200 bg-rose-50/50 space-y-1 shadow-xs">
        <div className="flex items-center justify-between text-rose-700">
          <span className="text-[11px] font-bold uppercase tracking-wider">Failed</span>
          <IconCriticalAlert className="w-4 h-4" />
        </div>
        <p className="text-2xl font-bold font-mono text-rose-700">{stats?.failed_imports || 0}</p>
      </div>

      <div className="p-4 rounded-lg border border-slate-200/90 bg-white space-y-1 shadow-xs">
        <div className="flex items-center justify-between text-slate-500">
          <span className="text-[11px] font-bold uppercase tracking-wider">
            {stats?.is_reset_active ? 'Active Rows (Reset)' : 'Active Rows'}
          </span>
          <IconOverlapHeatmap className="w-4 h-4" />
        </div>
        <p className={`text-2xl font-bold font-mono ${stats?.is_reset_active ? 'text-amber-700' : 'text-slate-900'}`}>
          {stats?.active_rows ?? stats?.total_rows_imported ?? 0}
        </p>
      </div>

      <div className="p-4 rounded-lg border border-amber-200 bg-amber-50/50 space-y-1 shadow-xs">
        <div className="flex items-center justify-between text-amber-700">
          <span className="text-[11px] font-bold uppercase tracking-wider">Avg Throughput</span>
          <IconEfficiencyTimer className="w-4 h-4" />
        </div>
        <p className="text-2xl font-bold font-mono text-amber-700">
          {stats?.average_throughput_rows_per_sec || 2450} <span className="text-xs font-medium font-sans">r/s</span>
        </p>
      </div>

      <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50 space-y-1 shadow-xs">
        <div className="flex items-center justify-between text-emerald-700">
          <span className="text-[11px] font-bold uppercase tracking-wider">Data Confidence</span>
          <IconShieldSecure className="w-4 h-4" />
        </div>
        <p className="text-2xl font-bold font-mono text-emerald-700">100%</p>
      </div>
    </div>
  );
};
