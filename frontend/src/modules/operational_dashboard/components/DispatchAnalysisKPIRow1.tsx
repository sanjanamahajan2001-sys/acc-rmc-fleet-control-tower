import React from 'react';
import { useDispatchAnalysisKPIs } from '../hooks/useDispatchAnalysisKPIs';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { AlertTriangle } from 'lucide-react';
import { IconTransitMixer, IconCycleStopwatch, IconDispatchAccuracy } from '../../../components/icons/LinealColorIcons';

export const DispatchAnalysisKPIRow1: React.FC = () => {
  const { data, loading, error, status } = useDispatchAnalysisKPIs();

  if (loading) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 bg-slate-50 border border-slate-200/60 rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0 text-rose-500" />
        <span>Failed to load operational metrics: {error}</span>
      </div>
    );
  }

  if (status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || !data) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-xl p-6 text-center text-xs text-slate-500 shadow-xs">
        No operational observations recorded for the active filter selection.
      </div>
    );
  }

  const getStatusBadge = (cadenceStatus: string) => {
    switch (cadenceStatus) {
      case 'Optimal':
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">OPTIMAL</span>;
      case 'Good':
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">GOOD</span>;
      case 'Warning':
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">WARNING</span>;
      default:
        return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">CRITICAL</span>;
    }
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg shadow-2xs overflow-hidden">
      {/* Group Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/70">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            Dispatch Execution &amp; Cadence Performance
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Real-time volume execution, departure pacing compliance, and delay recovery potential
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500">Overall Cadence Rhythm:</span>
          {getStatusBadge(data.cadence_status)}
        </div>
      </div>

      {/* 3 Cohesive Domain Clusters */}
      <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Cluster 1: Dispatch Volume & Lifecycle Completion */}
        <div className="bg-white border border-slate-200/90 rounded-lg p-3.5 flex flex-col justify-between hover:border-slate-300 hover:shadow-2xs transition-all relative overflow-hidden">
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="shrink-0 flex items-center justify-center">
                <IconTransitMixer className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 leading-tight">Dispatch Volume &amp; Completion</h4>
                <span className="text-[10px] text-slate-400 font-medium">Trip execution throughput</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 bg-white p-2.5 rounded-md border border-slate-200/70 mb-2.5 shadow-2xs">
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Total Dispatches</span>
                <span className="text-lg font-extrabold text-slate-900 font-mono tabular-nums">
                  {data.total_dispatches.toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-slate-500 font-medium ml-1">trips</span>
              </div>
              <div className="border-l border-slate-100 pl-2.5">
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Completed Trips</span>
                <span className="text-lg font-extrabold text-slate-900 font-mono tabular-nums">
                  {data.completed_dispatches.toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-slate-500 font-medium ml-1">closed</span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs">
            <span className="text-[11px] font-medium text-slate-500">On-Schedule Dispatches:</span>
            <span className="font-bold text-emerald-700 font-mono tabular-nums">
              {data.on_schedule_dispatches.toLocaleString('en-IN')} trips
            </span>
          </div>
        </div>

        {/* Cluster 2: Pacing Cadence & Interval Spacing */}
        <div className="bg-white border border-slate-200/90 rounded-lg p-3.5 flex flex-col justify-between hover:border-slate-300 hover:shadow-2xs transition-all relative overflow-hidden">
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="shrink-0 flex items-center justify-center">
                <IconCycleStopwatch className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 leading-tight">Pacing Cadence &amp; Departure Gap</h4>
                <span className="text-[10px] text-slate-400 font-medium">Truck departure rhythm</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 bg-white p-2.5 rounded-md border border-slate-200/70 mb-2.5 shadow-2xs">
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Avg Departure Gap</span>
                <span className="text-lg font-extrabold text-slate-900 font-mono tabular-nums">
                  {data.avg_interval_mins.toFixed(1)}m
                </span>
                <span className="text-[10px] text-slate-400 font-mono tabular-nums ml-1">±{data.interval_variance_mins.toFixed(1)}m</span>
              </div>
              <div className="border-l border-slate-100 pl-2.5">
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Avg Loading / Transit</span>
                <span className="text-lg font-extrabold text-slate-900 font-mono tabular-nums">
                  {data.avg_loading_mins.toFixed(1)}m
                </span>
                <span className="text-[10px] text-slate-400 font-mono tabular-nums ml-1">/ {data.avg_transit_mins.toFixed(1)}m</span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs">
            <span className="text-[11px] font-medium text-slate-500">Recommended Spacing:</span>
            <span className="font-bold text-blue-700 font-mono tabular-nums">
              {data.recommended_interval_mins.toFixed(1)} min target
            </span>
          </div>
        </div>

        {/* Cluster 3: Accuracy & Optimization Impact */}
        <div className="bg-white border border-slate-200/90 rounded-lg p-3.5 flex flex-col justify-between hover:border-slate-300 hover:shadow-2xs transition-all relative overflow-hidden">
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="shrink-0 flex items-center justify-center">
                <IconDispatchAccuracy className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 leading-tight">Accuracy &amp; Recovery Potential</h4>
                <span className="text-[10px] text-slate-400 font-medium">SLA compliance &amp; delay savings</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 bg-white p-2.5 rounded-md border border-slate-200/70 mb-2.5 shadow-2xs">
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">SLA Compliance</span>
                <span className="text-lg font-extrabold text-slate-900 font-mono tabular-nums">
                  {data.sla_compliance_pct.toFixed(1)}%
                </span>
                <span className="text-[10px] text-slate-400 font-sans ml-1">(Target: 80%)</span>
              </div>
              <div className="border-l border-slate-100 pl-2.5">
                <span className="text-[10px] font-bold uppercase text-slate-400 block">DAS Score</span>
                <span className="text-lg font-extrabold text-blue-700 font-mono tabular-nums">
                  {data.das_score_pct.toFixed(1)}%
                </span>
                <span className="text-[10px] text-slate-400 font-sans ml-1">Index</span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs">
            <span className="text-[11px] font-medium text-slate-500">Recoverable Delay:</span>
            <span className="font-bold text-emerald-700 font-mono tabular-nums">
              -{data.potential_delay_reduction_hrs.toFixed(1)} hrs saved
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export const DispatchAnalysisKPIRow2: React.FC = () => {
  // Empty fragment as all 10 KPIs are now grouped into the 3 cohesive operational clusters in Row1
  return null;
};
