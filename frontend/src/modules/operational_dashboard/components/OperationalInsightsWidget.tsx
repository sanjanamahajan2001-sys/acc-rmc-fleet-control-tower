import React from 'react';
import { useDispatchOperationalInsights, OperationalInsightItemDTO } from '../hooks/useDispatchOperationalInsights';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { AlertTriangle, Sparkles } from 'lucide-react';
import { IconSupervisorDirectives, IconQualityAward } from '../../../components/icons/LinealColorIcons';

export const OperationalInsightsWidget: React.FC = () => {
  const { data, loading, error, status } = useDispatchOperationalInsights();

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
        <h4 className="text-xs font-semibold text-rose-700">Failed to load operational recommendations</h4>
        <p className="text-[11px] text-slate-500 max-w-xs mt-1">{error}</p>
      </div>
    );
  }

  const isNoObs = status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || !data || data.insights.length === 0;

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg shadow-2xs flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <div>
        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-2 bg-slate-50/70">
          <div>
            <div className="flex items-center gap-2">
              <IconSupervisorDirectives className="w-4 h-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">Cadence Optimization &amp; Actions</h3>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Automated departure spacing strategies and calculated delay recovery potential
            </p>
          </div>
        </div>

        {/* Content */}
        {isNoObs ? (
          <div className="py-14 text-center space-y-2">
            <div className="text-xs font-semibold text-slate-600">NO OBSERVATIONS</div>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              No optimization recommendations available for active filters.
            </p>
          </div>
        ) : (
          <div className="p-4 space-y-3.5">
            {/* Strategy Overview Banner */}
            <div className="p-3 rounded-lg border border-slate-200/80 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  Recommended Strategy
                </span>
                <div className="text-sm font-extrabold text-blue-700 flex items-center gap-1.5 mt-0.5">
                  <IconQualityAward className="w-4 h-4" />
                  <span>{data.primary_pacing_strategy.replace(/_/g, ' ')}</span>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-sans font-medium">Target Spacing</span>
                  <span className="font-bold text-slate-900 tabular-nums">{data.target_departure_interval_mins.toFixed(1)}m</span>
                </div>
                <div className="border-l border-slate-200 pl-4">
                  <span className="text-slate-400 block text-[10px] uppercase font-sans font-medium">Recoverable Delay</span>
                  <span className="font-bold text-emerald-700 tabular-nums">{data.potential_recoverable_delay_hrs.toFixed(1)} hrs</span>
                </div>
              </div>
            </div>

            {/* Insights Cards */}
            <div className="space-y-2">
              {data.insights.map((insight: OperationalInsightItemDTO) => (
                <div
                  key={insight.id}
                  className="p-3 rounded-md border border-slate-200/80 bg-white hover:border-slate-300 transition-all space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-xs font-bold text-slate-900 truncate">{insight.title}</h4>
                    <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                      {insight.impact_level} IMPACT
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-snug">{insight.description}</p>
                  <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100 font-mono">
                    <span className="text-blue-700 text-[11px] font-semibold">{insight.primary_metric}</span>
                    <span className="font-bold text-emerald-700 tabular-nums">-{insight.estimated_delay_reduction_hrs.toFixed(1)}h recovery</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-[11px] text-slate-400 font-medium">
        <span>Continuous dispatch rhythm engine</span>
        <span className="font-mono text-slate-500">Pacing SLA</span>
      </div>
    </div>
  );
};
