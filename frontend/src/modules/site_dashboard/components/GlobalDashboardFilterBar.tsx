import { formatDisplayDate } from '../../../utils/date';
import React from 'react';
import { useDashboardFilters } from '../orchestration/DashboardFilterProvider';
import {
  IconCalendarDate,
  IconExcelSpreadsheet,
  IconEfficiencyTimer,
  IconDatasetDatabase,
  IconFilterFunnel,
} from '../../../components/icons/LinealColorIcons';

export const GlobalDashboardFilterBar: React.FC = () => {
  const { filters, metadata, plantOptions, customerOptions, setPlantFilter, setCustomerFilter, setDatasetTypeFilter } = useDashboardFilters();

  return (
    <div className="rounded-lg p-4 space-y-3 bg-white border border-slate-200/90 shadow-2xs">
      {/* Top Row: Informational Read-Only Dataset Metadata Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200 text-xs">
        <div className="flex flex-wrap items-center gap-3 font-medium text-slate-600">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200">
            <IconCalendarDate className="w-4 h-4" />
            <span>Op Date: <strong className="text-slate-900 font-mono font-semibold">{metadata?.operational_date ? formatDisplayDate(metadata.operational_date) : '—'}</strong></span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200">
            <IconExcelSpreadsheet className="w-4 h-4" />
            <span>Dispatches: <strong className="text-slate-900 font-mono font-semibold">{metadata?.total_dispatches ? metadata.total_dispatches.toLocaleString() : '—'}</strong></span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200">
            <IconEfficiencyTimer className="w-4 h-4" />
            <span>Imported: <strong className="text-slate-900 font-mono font-semibold">{metadata?.import_timestamp ? new Date(metadata.import_timestamp).toLocaleTimeString() : 'Just Now'}</strong></span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <IconDatasetDatabase className="w-4 h-4" />
          <span>DATASET ID: <strong className="text-slate-800 font-mono">{metadata?.dataset_id || '—'}</strong> ({metadata?.dataset_status || 'ACTIVE'})</span>
        </div>
      </div>

      {/* Bottom Row: Dynamic Active Dropdown Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* 1. Dynamic Plant Filter Dropdown */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-slate-600">
            <IconFilterFunnel className="w-3.5 h-3.5" /> Plant Selection
          </label>
          <select
            value={filters.plant_id}
            onChange={(e) => setPlantFilter(e.target.value)}
            className="w-full bg-slate-50/70 border border-slate-200 text-slate-900 rounded-md px-3 py-2 text-xs font-semibold focus:outline-none focus:border-blue-700 focus:bg-white transition-colors cursor-pointer min-h-[38px]"
          >
            {plantOptions.map((p) => (
              <option key={p.id} value={p.id} className="bg-white text-slate-900">
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* 2. Dynamic Customer Filter Dropdown */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-slate-600">
            <IconFilterFunnel className="w-3.5 h-3.5" /> Customer Filter
          </label>
          <select
            value={filters.customer_id}
            onChange={(e) => setCustomerFilter(e.target.value)}
            className="w-full bg-slate-50/70 border border-slate-200 text-slate-900 rounded-md px-3 py-2 text-xs font-semibold focus:outline-none focus:border-blue-700 focus:bg-white transition-colors cursor-pointer min-h-[38px]"
          >
            {customerOptions.map((c) => (
              <option key={c.id} value={c.id} className="bg-white text-slate-900">
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {/* 3. Dataset Type Filter Dropdown */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-slate-600">
            <IconFilterFunnel className="w-3.5 h-3.5" /> Dataset Scope
          </label>
          <select
            value={filters.dataset_type}
            onChange={(e) => setDatasetTypeFilter(e.target.value)}
            className="w-full bg-slate-50/70 border border-slate-200 text-slate-900 rounded-md px-3 py-2 text-xs font-semibold focus:outline-none focus:border-blue-700 focus:bg-white transition-colors cursor-pointer min-h-[38px]"
          >
            <option value="ALL" className="bg-white text-slate-900">All Scope (Total Operational Volume)</option>
            <option value="HISTORICAL" className="bg-white text-slate-900">Historical ERP Dispatches</option>
            <option value="LIVE" className="bg-white text-slate-900">Live Real-time Batching</option>
          </select>
        </div>
      </div>
    </div>
  );
};
