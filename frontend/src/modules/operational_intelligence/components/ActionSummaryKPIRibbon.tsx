import React from 'react';
import { Clock, CheckCircle2, AlertTriangle, XCircle, DollarSign, RefreshCw } from 'lucide-react';
import { IconSupervisorDirectives, IconCycleStopwatch, IconCalendarCheckmark, IconCriticalAlert } from '../../../components/icons/LinealColorIcons';
import { ActionLogItem } from '../api/actionExecutionApi';

interface ActionSummaryKPIRibbonProps {
  actions: ActionLogItem[];
  isLoading: boolean;
  onRefresh: () => void;
}

export const ActionSummaryKPIRibbon: React.FC<ActionSummaryKPIRibbonProps> = ({
  actions,
  isLoading,
  onRefresh,
}) => {
  const activeRecs = actions.length;
  const pendingCount = actions.filter((a) => a.action_status === 'PENDING').length;
  const acceptedCount = actions.filter((a) => a.action_status === 'ACCEPTED').length;
  const inProgressCount = actions.filter((a) => a.action_status === 'IN_PROGRESS').length;
  const executedCount = actions.filter((a) => a.action_status === 'EXECUTED').length;
  const deferredCount = actions.filter((a) => a.action_status === 'DEFERRED').length;
  const rejectedCount = actions.filter((a) => a.action_status === 'REJECTED').length;

  const totalEstimatedAvoidedExposure = actions.reduce((acc, a) => {
    return acc + (a.estimated_avoided_exposure_inr || 0);
  }, 0);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-5 mb-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wider uppercase border bg-blue-50 border-blue-200 text-blue-700">
              Dispatch Command
            </span>
            <span className="text-[11px] font-mono font-medium text-slate-500">Control Tower Decision &amp; Action Execution Canvas</span>
          </div>
          <h2 className="text-base font-bold tracking-tight text-slate-900 mt-1">
            Control Tower Action Summary &amp; Financial Exposure Ribbon
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <span className="text-[10px] font-bold uppercase tracking-wider block text-slate-500">Avoided Penalty Potential</span>
            <span className="text-sm font-bold font-mono tabular-nums text-emerald-700">{formatINR(totalEstimatedAvoidedExposure)}</span>
          </div>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold rounded-md border border-slate-200 bg-white text-slate-700 transition disabled:opacity-50 hover:bg-slate-50 shrink-0 shadow-xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh Pipeline
          </button>
        </div>
      </div>

      {/* 4 Clean Operational Metric Clusters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Pending Triage */}
        <div className="border border-amber-200 bg-amber-50/60 rounded-md p-4 flex items-center justify-between shadow-2xs transition">
          <div className="space-y-1">
            <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-amber-800">
              <Clock className="w-3.5 h-3.5" /> Requires Action (Pending)
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-amber-900">{pendingCount}</div>
            <span className="text-[10px] font-medium text-amber-700">Awaiting dispatcher authorization</span>
          </div>
          <div className="shrink-0 flex items-center justify-center">
            <IconSupervisorDirectives className="w-6 h-6" />
          </div>
        </div>

        {/* 2. Active in Pipeline (Approved + In Progress) */}
        <div className="border border-blue-200 bg-blue-50/60 rounded-md p-4 flex items-center justify-between shadow-2xs transition">
          <div className="space-y-1">
            <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-blue-800">
              <CheckCircle2 className="w-3.5 h-3.5" /> Approved &amp; Staging
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-blue-900">{acceptedCount + inProgressCount}</div>
            <span className="text-[10px] font-medium text-blue-700">{acceptedCount} Intent Approved • {inProgressCount} En Route</span>
          </div>
          <div className="shrink-0 flex items-center justify-center">
            <IconCycleStopwatch className="w-6 h-6" />
          </div>
        </div>

        {/* 3. Confirmed Executions */}
        <div className="border border-emerald-200 bg-emerald-50/60 rounded-md p-4 flex items-center justify-between shadow-2xs transition">
          <div className="space-y-1">
            <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-emerald-800">
              <CheckCircle2 className="w-3.5 h-3.5" /> Executed &amp; Resolved
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-emerald-900">{executedCount}</div>
            <span className="text-[10px] font-medium text-emerald-700">Physically confirmed at plant / job site</span>
          </div>
          <div className="shrink-0 flex items-center justify-center">
            <IconCalendarCheckmark className="w-6 h-6" />
          </div>
        </div>

        {/* 4. Exceptions & Total Pipeline */}
        <div className="border border-slate-200 bg-slate-50 rounded-md p-4 flex items-center justify-between shadow-2xs transition">
          <div className="space-y-1">
            <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 text-slate-700">
              <AlertTriangle className="w-3.5 h-3.5" /> Deferred &amp; Rejected
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-slate-900">{deferredCount + rejectedCount}</div>
            <span className="text-[10px] font-medium text-slate-500">{deferredCount} Deferred • {rejectedCount} Rejected with reason</span>
          </div>
          <div className="shrink-0 flex items-center justify-center">
            <IconCriticalAlert className="w-6 h-6" />
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs font-mono text-slate-500">
        <div>Total Directives Evaluated: <strong className="text-slate-900 tabular-nums">{activeRecs}</strong></div>
        <div>Estimated Avoided Exposure: <strong className="text-emerald-700 tabular-nums">{formatINR(totalEstimatedAvoidedExposure)}</strong> (*Decision-time estimate)</div>
      </div>
    </div>
  );
};
