import React from 'react';
import { useDispatchDelayAnalytics } from '../hooks/useDispatchDelayAnalytics';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { AlertTriangle, AlertCircle } from 'lucide-react';
import { IconCycleStopwatch } from '../../../components/icons/LinealColorIcons';

export const DispatchDelayAnalyticsWidget: React.FC = () => {
  const { data, loading, error, status } = useDispatchDelayAnalytics();

  if (loading) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs min-h-[360px] animate-pulse">
        <div className="h-5 bg-slate-100 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-16 bg-slate-50 rounded-xl"></div>
          <div className="h-16 bg-slate-50 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs min-h-[360px] flex flex-col justify-center items-center text-center">
        <AlertTriangle className="w-6 h-6 text-rose-500 mb-2" />
        <h4 className="text-xs font-semibold text-rose-700">Failed to load delay analytics</h4>
        <p className="text-[11px] text-slate-500 max-w-xs mt-1">{error}</p>
      </div>
    );
  }

  const isNoObs = status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || !data || data.categories.length === 0;

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg shadow-2xs flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div>
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2 bg-slate-50/70">
          <div>
            <div className="flex items-center gap-2">
              <IconCycleStopwatch className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">Root-Cause Delay Breakdown</h3>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Cumulative idle time categorization across queues, unloading, and departure pacing
            </p>
          </div>
        </div>

        {/* Content */}
        {isNoObs ? (
          <div className="py-14 text-center space-y-2">
            <div className="text-xs font-semibold text-slate-600">NO OBSERVATIONS</div>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              No delay observations available for active filters.
            </p>
          </div>
        ) : (
          <div className="p-4 space-y-3.5">
            {/* Cumulative Delay Bar */}
            <div className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  Total Delay Incurred
                </span>
                <div className="text-2xl font-extrabold text-slate-900 font-mono tabular-nums mt-0.5">
                  {data.total_delay_hours.toFixed(1)}{' '}
                  <span className="text-xs font-normal text-slate-500 font-sans">Hours Lost</span>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-sans font-medium">Queue</span>
                  <span className="font-bold text-amber-700 tabular-nums">{data.buildup_delay_hours.toFixed(1)}h</span>
                </div>
                <div className="border-l border-slate-200 pl-4">
                  <span className="text-slate-400 block text-[10px] uppercase font-sans font-medium">Unload</span>
                  <span className="font-bold text-rose-700 tabular-nums">{data.unload_delay_hours.toFixed(1)}h</span>
                </div>
                <div className="border-l border-slate-200 pl-4">
                  <span className="text-slate-400 block text-[10px] uppercase font-sans font-medium">Variance</span>
                  <span className="font-bold text-blue-700 tabular-nums">{data.sequence_variance_delay_hours.toFixed(1)}h</span>
                </div>
              </div>
            </div>

            {/* Delay Categories */}
            <div className="space-y-2">
              {data.categories.map((cat, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-md border border-slate-200/80 bg-white hover:border-slate-300 transition-all flex items-start justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900 truncate">{cat.category_name}</span>
                      <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-bold border ${
                        cat.severity === 'HIGH'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : cat.severity === 'MEDIUM'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}>
                        {cat.severity}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 leading-snug">{cat.recommendation}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-sm font-extrabold text-slate-900 font-mono tabular-nums">{cat.delay_hours.toFixed(1)}h</div>
                    <div className="text-[10px] text-slate-400 font-mono tabular-nums">{cat.percentage_contribution.toFixed(1)}% · {cat.affected_trips_count} trips</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-[11px] text-slate-400 font-medium">
        <span>Derived from live ERP timestamps</span>
        <span className="font-mono text-slate-500">Root Cause Engine</span>
      </div>
    </div>
  );
};
