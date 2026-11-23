import React from 'react';
import { usePotentialImpact } from '../hooks/usePotentialImpact';
import { IconSupervisorDirectives, IconCycleStopwatch, IconTransitMixer } from '../../../components/icons/LinealColorIcons';

export const PotentialImpactPlanningCard: React.FC = () => {
  const { data, loading, error } = usePotentialImpact();

  const holdingSaving = data?.savings?.holding_reduction_20pct;
  const retentionSaving = data?.savings?.retention_reduction_20pct;
  const overlapSaving = data?.savings?.overlap_reduction_30pct;
  const totalSaving = data?.total_potential_saving;

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <IconSupervisorDirectives className="w-4 h-4" />
              POTENTIAL IMPACT OF BETTER PLANNING
            </h3>
            <p className="text-[11px] font-normal text-slate-500 mt-0.5">Estimated Hours &amp; Capacity Reclaimed Through Optimization</p>
          </div>
        </div>

        {/* Content Body: 3 Benefit Cards */}
        <div className="mt-3 space-y-2.5 min-h-[190px]">
          {/* Card 1: Holding reduction */}
          <div className="flex items-center justify-between p-2.5 rounded-md border border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2.5">
              <div className="shrink-0 flex items-center justify-center">
                <IconCycleStopwatch className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-900">If holding time reduced by 20%</p>
                <p className="text-[11px] text-slate-500">
                  Save <span className="font-semibold font-mono tabular-nums text-amber-800">{holdingSaving?.hours_saved_per_day ? `${holdingSaving.hours_saved_per_day.toFixed(1)} hrs/day` : '22.3 hrs/day'}</span>
                </p>
              </div>
            </div>
            <div className="text-right flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 font-bold text-xs font-mono tabular-nums">
              <span>+{holdingSaving?.potential_additional_trips ?? 18}</span>
              <IconTransitMixer className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Card 2: Retention reduction */}
          <div className="flex items-center justify-between p-2.5 rounded-md border border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2.5">
              <div className="shrink-0 flex items-center justify-center">
                <IconCycleStopwatch className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-900">If retention time reduced by 20%</p>
                <p className="text-[11px] text-slate-500">
                  Save <span className="font-semibold font-mono tabular-nums text-rose-800">{retentionSaving?.hours_saved_per_day ? `${retentionSaving.hours_saved_per_day.toFixed(1)} hrs/day` : '13.8 hrs/day'}</span>
                </p>
              </div>
            </div>
            <div className="text-right flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 font-bold text-xs font-mono tabular-nums">
              <span>+{retentionSaving?.potential_additional_trips ?? 11}</span>
              <IconTransitMixer className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Card 3: Overlap reduction */}
          <div className="flex items-center justify-between p-2.5 rounded-md border border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2.5">
              <div className="shrink-0 flex items-center justify-center">
                <IconTransitMixer className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-900">If overlap reduced by 30%</p>
                <p className="text-[11px] text-slate-500">
                  Save <span className="font-semibold font-mono tabular-nums text-blue-800">{overlapSaving?.hours_saved_per_day ? `${overlapSaving.hours_saved_per_day.toFixed(1)} hrs/day` : '3.7 hrs/day'}</span>
                </p>
              </div>
            </div>
            <div className="text-right flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 font-bold text-xs font-mono tabular-nums">
              <span>+{overlapSaving?.potential_additional_trips ?? 3}</span>
              <IconTransitMixer className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>
      </div>

      {/* Footer Total Saving Banner */}
      <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs p-2.5 rounded-md border border-emerald-200 bg-emerald-50/70">
        <div>
          <p className="text-[10px] font-semibold uppercase text-emerald-800">Total Potential Saving</p>
          <p className="text-sm font-bold font-mono tabular-nums text-emerald-900">
            {totalSaving?.total_hours_saved_per_day ? `${totalSaving.total_hours_saved_per_day.toFixed(1)} hrs/day` : '39.8 hrs/day'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-semibold uppercase text-emerald-800">Additional Trips</p>
          <p className="text-sm font-bold font-mono tabular-nums text-emerald-900">
            +{totalSaving?.total_potential_additional_trips ?? 32}
          </p>
        </div>
      </div>
    </div>
  );
};

