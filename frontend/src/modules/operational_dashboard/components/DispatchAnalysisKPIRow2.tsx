import React from 'react';
import { useDispatchAnalysisKPIs } from '../hooks/useDispatchAnalysisKPIs';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { AlertTriangle } from 'lucide-react';
import { IconCalendarCheckmark, IconEfficiencyTimer, IconCycleStopwatch, IconPlantSiteDashboard, IconSupervisorDirectives } from '../../../components/icons/LinealColorIcons';

export const DispatchAnalysisKPIRow2: React.FC = () => {
  const { data, loading, error, status } = useDispatchAnalysisKPIs();

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 animate-pulse">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-24 bg-white border border-slate-200/80 rounded-xl p-4"></div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
        <AlertTriangle className="w-4 h-4 shrink-0 text-rose-500" />
        <span>Failed to load secondary dispatch metrics: {error}</span>
      </div>
    );
  }

  if (status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || !data) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {['COMPLETED DISPATCHES', 'AVG LOADING / TRANSIT', 'OPTIMIZED INTERVAL', 'CADENCE STATUS', 'OPTIMIZATION IMPACT'].map((t, idx) => (
          <div key={idx} className="p-4 rounded-xl bg-white border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-500 block">{t}</span>
            <div className="text-xl font-bold text-slate-400 mt-1">—</div>
            <span className="text-[10px] text-slate-400 block mt-0.5">No observations</span>
          </div>
        ))}
      </div>
    );
  }

  const getStatusBadge = (cadenceStatus: string) => {
    switch (cadenceStatus) {
      case 'Optimal':
        return <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">OPTIMAL</span>;
      case 'Good':
        return <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">GOOD</span>;
      case 'Warning':
        return <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">WARNING</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">CRITICAL</span>;
    }
  };

  const cards = [
    {
      title: 'Completed Dispatches',
      value: data.completed_dispatches.toLocaleString('en-IN'),
      unit: `/ ${data.total_dispatches.toLocaleString('en-IN')}`,
      subtext: 'Trips with confirmed return time',
      icon: IconCalendarCheckmark,
    },
    {
      title: 'Avg Loading & Transit',
      value: `${data.avg_loading_mins.toFixed(1)}m`,
      unit: `/ ${data.avg_transit_mins.toFixed(1)}m`,
      subtext: 'Plant holding (T2a) & Site transit (T1)',
      icon: IconEfficiencyTimer,
    },
    {
      title: 'Recommended Interval',
      value: `${data.recommended_interval_mins.toFixed(1)}m`,
      unit: 'Target',
      subtext: 'Calculated optimal departure spacing',
      icon: IconCycleStopwatch,
    },
    {
      title: 'Cadence Health',
      value: data.cadence_status,
      badge: getStatusBadge(data.cadence_status),
      subtext: 'Overall departure rhythm status',
      icon: IconPlantSiteDashboard,
    },
    {
      title: 'Potential Recovery',
      value: `${data.potential_delay_reduction_hrs.toFixed(1)}h`,
      unit: 'Saved',
      subtext: 'Recoverable queue holding hours',
      icon: IconSupervisorDirectives,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
      {cards.map((c, idx) => {
        const IconComp = c.icon;
        return (
          <div
            key={idx}
            className="bg-white border border-slate-200/90 rounded-lg p-3.5 shadow-2xs hover:border-slate-300 transition-all flex flex-col justify-between"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-600 truncate">{c.title}</span>
              <div className="shrink-0 flex items-center justify-center">
                <IconComp className="w-4 h-4" />
              </div>
            </div>

            <div className="mt-2.5">
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-extrabold text-slate-900 font-mono tabular-nums tracking-tight">{c.value}</span>
                {c.unit && <span className="text-xs font-semibold text-slate-500">{c.unit}</span>}
                {c.badge && <div className="ml-auto">{c.badge}</div>}
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate mt-0.5">{c.subtext}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
