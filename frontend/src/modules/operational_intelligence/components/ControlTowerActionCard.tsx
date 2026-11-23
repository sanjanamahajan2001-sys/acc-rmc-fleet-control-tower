import React from 'react';
import { Clock, CheckCircle2, Play, AlertCircle, Info, ArrowRight } from 'lucide-react';
import { IconBatchingPlantFactory, IconTransitMixer, IconCriticalAlert, IconSyncRefresh, IconSupervisorDirectives } from '../../../components/icons/LinealColorIcons';
import { ActionLogItem } from '../api/actionExecutionApi';

interface ControlTowerActionCardProps {
  action: ActionLogItem;
  onAccept: (action: ActionLogItem) => void;
  onStartProgress: (action: ActionLogItem) => void;
  onConfirmExecution: (action: ActionLogItem) => void;
  onReject: (action: ActionLogItem) => void;
  onDefer: (action: ActionLogItem) => void;
  onViewAudit: (action: ActionLogItem) => void;
  readOnly?: boolean;
}

export const ControlTowerActionCard: React.FC<ControlTowerActionCardProps> = ({
  action,
  onAccept,
  onStartProgress,
  onConfirmExecution,
  onReject,
  onDefer,
  onViewAudit,
  readOnly = false,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md inline-flex items-center gap-1 bg-amber-50 border-amber-300 text-amber-800">
            <Clock className="w-3 h-3" /> PENDING DISPATCHER ACTION
          </span>
        );
      case 'ACCEPTED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md inline-flex items-center gap-1 bg-blue-50 border-blue-200 text-blue-800">
            <CheckCircle2 className="w-3 h-3" /> INTENT APPROVED (AWAITING TRUCK)
          </span>
        );
      case 'IN_PROGRESS':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md inline-flex items-center gap-1 bg-blue-100 border-blue-300 text-blue-900">
            <Play className="w-3 h-3" /> BUFFER IN EFFECT
          </span>
        );
      case 'EXECUTED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md inline-flex items-center gap-1 bg-emerald-50 border-emerald-300 text-emerald-800">
            <CheckCircle2 className="w-3 h-3" /> PHYSICALLY CONFIRMED
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md inline-flex items-center gap-1 bg-rose-50 border-rose-300 text-rose-800">
            <AlertCircle className="w-3 h-3" /> REJECTED WITH REASON
          </span>
        );
      case 'DEFERRED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md inline-flex items-center gap-1 bg-slate-100 border-slate-300 text-slate-700">
            <Clock className="w-3 h-3" /> DEFERRED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold border rounded-md bg-slate-100 border-slate-300 text-slate-800">
            {status}
          </span>
        );
    }
  };

  const getDomainConfig = () => {
    switch (action.action_type) {
      case 'STAGGER_LOADING':
        return {
          title: 'Plant Loading Offset Directive',
          subtitle: `Stagger mixer loading by +${action.action_parameters?.offset_mins || 15} mins`,
          domain: 'Plant Batch Queue',
          badgeClass: 'bg-amber-50 border-amber-300 text-amber-800',
          iconClass: 'bg-amber-100 border-amber-300 text-amber-800',
          icon: IconBatchingPlantFactory,
        };
      case 'TRANSIT_BUFFER':
        return {
          title: 'Road Transit Buffer Directive',
          subtitle: `Stage departure +${action.action_parameters?.buffer_mins || 20} mins earlier`,
          domain: 'Corridor Traffic',
          badgeClass: 'bg-blue-50 border-blue-200 text-blue-800',
          iconClass: 'bg-blue-100 border-blue-300 text-blue-800',
          icon: IconTransitMixer,
        };
      case 'SLA_PRIORITIZE':
        return {
          title: 'Critical Customer SLA Escalation',
          subtitle: `Elevate dispatch queue priority to ${action.action_parameters?.priority_level || 'URGENT'}`,
          domain: 'Contractual SLA Delivery',
          badgeClass: 'bg-rose-50 border-rose-300 text-rose-800',
          iconClass: 'bg-rose-100 border-rose-300 text-rose-800',
          icon: IconCriticalAlert,
        };
      case 'INTRA_ZONE_REALLOCATE':
        return {
          title: 'Intra-Zone Cluster Reallocation',
          subtitle: `Shift batching to ${action.action_parameters?.target_plant_code || 'Partner Plant'} (+${action.action_parameters?.predicted_improvement_mins || 14.5}m gain)`,
          domain: 'Plant Network Reallocation',
          badgeClass: 'bg-emerald-50 border-emerald-300 text-emerald-800',
          iconClass: 'bg-emerald-100 border-emerald-300 text-emerald-800',
          icon: IconSyncRefresh,
        };
      default:
        return {
          title: action.action_type.replace(/_/g, ' '),
          subtitle: 'Execute recommended dispatch protocol',
          domain: 'Operational Optimization',
          badgeClass: 'bg-slate-50 border-slate-200 text-slate-800',
          iconClass: 'bg-slate-100 border-slate-200 text-slate-800',
          icon: IconSupervisorDirectives,
        };
    }
  };

  const config = getDomainConfig();
  const DomainIcon = config.icon;

  return (
    <div
      className="bg-white border border-slate-200/90 rounded-lg p-5 shadow-xs transition-all duration-200 flex flex-col justify-between"
      data-testid={`action-card-${action.action_id}`}
    >
      <div className="space-y-4">
        {/* Header Ribbon: Domain + Status */}
        <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase border flex items-center gap-1 ${config.badgeClass}`}>
              <DomainIcon className="w-3 h-3" />
              {config.domain}
            </span>
            <span className="text-[11px] font-mono font-bold text-slate-500">
              {action.action_id}
            </span>
          </div>
          <div>{getStatusBadge(action.action_status)}</div>
        </div>

        {/* Dispatch Code & Specific Recommended Directive */}
        <div>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold tracking-tight text-slate-900">
              {action.dispatch_code || action.dispatch_id}
            </h3>
            <span className="text-[11px] font-mono font-medium text-slate-500">
              {action.plant_code} ➔ {action.customer_code}
            </span>
          </div>

          {/* Action Directive Box (What should the user do?) */}
          <div className={`mt-2.5 p-3 rounded-md border flex items-start gap-2.5 shadow-2xs ${config.badgeClass}`}>
            <div className={`p-1.5 rounded-md border shrink-0 bg-white/80 ${config.iconClass}`}>
              <DomainIcon className="w-4 h-4" />
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] font-bold uppercase tracking-wider block opacity-90">
                Recommended Operational Directive
              </span>
              <p className="text-xs font-bold leading-tight text-slate-900">
                {config.subtitle}
              </p>
            </div>
          </div>
        </div>

        {/* Operational Trigger & Evidence Summary (Why does it need attention?) */}
        <div className="p-3.5 rounded-md border border-slate-200/80 bg-slate-50 space-y-2 text-xs font-sans">
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <span>Operational Trigger &amp; Impact</span>
            <span>Est. Avoided Loss</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2.5">
            <p className="text-xs font-medium leading-relaxed text-slate-800">
              {action.dispatcher_notes
                ? action.dispatcher_notes.replace(/Trigger: /g, '').split('Ranking:')[0].trim()
                : `Predicted operational variance at ${action.plant_code} requiring dispatch buffer.`}
            </p>
            <div className="text-left sm:text-right shrink-0 pt-1 sm:pt-0 border-t sm:border-t-0 border-slate-200">
              <span className="text-sm font-bold font-mono tabular-nums text-emerald-700">
                {action.predicted_risk_exposure_inr !== null && action.predicted_risk_exposure_inr !== undefined
                  ? `₹${Math.round(action.predicted_risk_exposure_inr).toLocaleString('en-IN')}`
                  : 'SLA Buffer'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Controls & Governance Actions */}
      <div className="pt-4 border-t border-slate-100 mt-4 flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onViewAudit(action)}
          className="text-xs font-bold flex items-center gap-1 py-1 cursor-pointer text-blue-700 hover:text-blue-800 hover:underline"
        >
          <Info className="w-3.5 h-3.5" /> View Full Lineage
        </button>

        <div className="flex items-center gap-2">
          {readOnly ? (
            <span className="text-[11px] font-medium text-slate-500 italic">
              View-only mode: Action execution disabled
            </span>
          ) : (
            <>
              {action.action_status === 'PENDING' && (
                <>
                  <button
                    type="button"
                    onClick={() => onReject(action)}
                    className="px-2.5 py-1.5 text-xs font-bold rounded-md border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 transition cursor-pointer"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => onDefer(action)}
                    className="px-2.5 py-1.5 text-xs font-bold rounded-md border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                  >
                    Defer
                  </button>
                  <button
                    type="button"
                    onClick={() => onAccept(action)}
                    className="px-3 py-1.5 text-white text-xs font-bold rounded-md bg-blue-700 hover:bg-blue-800 shadow-xs transition flex items-center gap-1.5 cursor-pointer"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" /> Accept Intent
                  </button>
                </>
              )}

              {action.action_status === 'ACCEPTED' && (
                <button
                  type="button"
                  onClick={() => onStartProgress(action)}
                  className="px-3 py-1.5 text-white text-xs font-bold rounded-md bg-blue-700 hover:bg-blue-800 shadow-xs transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5" /> Start Progress
                </button>
              )}

              {(action.action_status === 'ACCEPTED' || action.action_status === 'IN_PROGRESS') && (
                <button
                  type="button"
                  onClick={() => onConfirmExecution(action)}
                  className="px-3 py-1.5 text-white text-xs font-bold rounded-md bg-emerald-700 hover:bg-emerald-800 shadow-xs transition flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Execution
                </button>
              )}
            </>
          )}

          {action.action_status === 'EXECUTED' && (
            <span className="text-xs font-bold flex items-center gap-1 text-emerald-700">
              <CheckCircle2 className="w-4 h-4" /> Executed &amp; Verified
            </span>
          )}

          {action.action_status === 'REJECTED' && (
            <span className="text-xs font-bold flex items-center gap-1 text-rose-700">
              <IconCriticalAlert className="w-4 h-4" /> Rejected
            </span>
          )}

          {action.action_status === 'DEFERRED' && (
            <span className="text-xs font-bold flex items-center gap-1 text-slate-600">
              <Clock className="w-4 h-4" /> Deferred
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
