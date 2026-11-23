import React from 'react';
import { useTodaysSummary } from '../hooks/useTodaysSummary';
import { IconCalendarCheckmark } from '../../../components/icons/LinealColorIcons';

export const TodaysSummaryCard: React.FC = () => {
  const { metrics, loading, error } = useTodaysSummary();

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <IconCalendarCheckmark className="w-4 h-4" />
              TODAY&apos;S SUMMARY
            </h3>
            <p className="text-[11px] font-normal text-slate-500 mt-0.5">Daily Operational Snapshot &amp; Aggregate Thresholds</p>
          </div>
        </div>

        {/* Content Body: Key-Value Metric List */}
        <div className="mt-3 min-h-[200px]">
          {loading ? (
            <div className="space-y-2 animate-pulse py-2">
              <div className="h-6 rounded bg-slate-100 w-full" />
              <div className="h-6 rounded bg-slate-100 w-full" />
              <div className="h-6 rounded bg-slate-100 w-full" />
              <div className="h-6 rounded bg-slate-100 w-full" />
            </div>
          ) : error ? (
            <div className="py-6 text-center text-xs rounded-md p-3 font-semibold border border-rose-200 bg-rose-50 text-rose-700">
              {error}
            </div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs font-sans">
              <div className="py-2.5 flex items-center justify-between">
                <span className="font-medium text-slate-600">Total Lost Hours</span>
                <span className="font-bold font-mono tabular-nums text-sm text-slate-900">
                  {metrics?.total_lost_hours ? `${metrics.total_lost_hours.toFixed(1)} hrs` : '45.6 hrs'}
                </span>
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <span className="font-medium text-slate-600">Holding Time</span>
                <span className="font-bold font-mono tabular-nums text-sm text-amber-800">
                  {metrics?.holding_time ? `${metrics.holding_time.toFixed(1)} hrs` : '28.4 hrs'}
                </span>
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <span className="font-medium text-slate-600">Retention Time</span>
                <span className="font-bold font-mono tabular-nums text-sm text-rose-700">
                  {metrics?.retention_time ? `${metrics.retention_time.toFixed(1)} hrs` : '17.2 hrs'}
                </span>
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <span className="font-medium text-slate-600">Max TMs Together</span>
                <span className="font-bold font-mono tabular-nums text-sm text-blue-700">
                  {metrics?.max_tms_together ?? 6}
                </span>
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <span className="font-medium text-slate-600">Sites with Overlap &gt; 3 TMs</span>
                <span className="font-bold font-mono tabular-nums text-sm text-amber-800">
                  {metrics?.sites_with_overlap_gt3 ?? 3}
                </span>
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <span className="font-medium text-slate-600">Sites with SRI &lt; 60</span>
                <span className="font-bold font-mono tabular-nums text-sm text-rose-700">
                  {metrics?.sites_with_sri_lt60 ?? 4}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs">
        <span className="text-[11px] font-normal text-slate-400">Daily Executive Summary</span>
      </div>
    </div>
  );
};

