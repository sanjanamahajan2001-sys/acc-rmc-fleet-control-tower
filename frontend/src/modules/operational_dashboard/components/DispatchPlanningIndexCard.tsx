import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { IconCalendarDate } from '../../../components/icons/LinealColorIcons';
import { KPICardItemDTO, AvailabilityEnum } from '../hooks/useExecutiveKPIs';

interface DispatchPlanningIndexCardProps {
  data: KPICardItemDTO;
  loading?: boolean;
}

export const DispatchPlanningIndexCard: React.FC<DispatchPlanningIndexCardProps> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs animate-pulse space-y-3">
        <div className="flex items-center justify-between">
          <div className="w-8 h-8 rounded-md bg-slate-100" />
          <div className="h-4 w-20 bg-slate-100 rounded" />
        </div>
        <div className="h-7 w-16 bg-slate-100 rounded" />
        <div className="h-1.5 w-full bg-slate-100 rounded" />
      </div>
    );
  }

  const isAvailable = data.availability === AvailabilityEnum.AVAILABLE && data.current_value !== null;
  const val = isAvailable ? Number(data.current_value) : 0;
  const target = data.target ?? 85;

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div>
        {/* Header: Square Icon + Title */}
        <div className="flex items-center gap-2.5">
          <div className="shrink-0 flex items-center justify-center">
            <IconCalendarDate className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
            DISPATCH PLANNING INDEX (DPI)
          </span>
        </div>

        {/* Main Metric & Comparison */}
        <div className="mt-3 flex items-baseline justify-between">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-slate-900">
              {isAvailable ? val : 'N/A'}
            </span>
          </div>

          {isAvailable && data.variance !== undefined && data.variance !== null && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-normal text-slate-500 text-[11px]">vs Yesterday 81</span>
              <span
                className={`px-1.5 py-0.5 rounded-md text-[11px] font-medium font-mono tabular-nums flex items-center gap-0.5 border ${
                  data.variance >= 0
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-rose-50 text-rose-700 border-rose-200'
                }`}
              >
                {data.variance >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {data.variance >= 0 ? `+${data.variance}` : `${data.variance}`}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Target Progress Bar Footer */}
      <div className="mt-4 pt-2.5 border-t border-slate-100 space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="font-medium text-slate-500">Target &gt; {target}</span>
        </div>
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(val, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
};

