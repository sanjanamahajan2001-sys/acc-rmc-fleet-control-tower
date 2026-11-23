import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Zap, ArrowRight, CheckCircle2, ShieldAlert, AlertTriangle, ArrowUpRight, Flame, Clock } from 'lucide-react';

export interface CriticalAlertItem {
  id: string;
  alert_type: string;
  severity: string;
  message?: string;
  business_impact?: string;
  recommended_action?: string;
  actual_value?: string | number;
  unit?: string;
  plant_id?: string;
  customer_id?: string;
  detected_at?: string;
}

export interface PendingActionItem {
  action_id: string;
  action_type: string;
  plant_code: string;
  customer_code?: string;
  action_status: string;
  predicted_risk_exposure_inr?: number;
}

interface HomeNeedsAttentionWidgetProps {
  alerts: CriticalAlertItem[];
  alertsLoading: boolean;
  alertsError: boolean;
  actions: PendingActionItem[];
  actionsLoading: boolean;
  actionsError: boolean;
}

/** Human-friendly format for exception titles */
const formatExceptionType = (type: string): string => {
  switch (type) {
    case 'PLANT_HOLDING_BOTTLENECK':
      return 'Plant Batch Queue Bottleneck';
    case 'SITE_RETENTION_EXCESSIVE':
      return 'Customer Site Unloading Overrun';
    case 'TRANSIT_DELAY_EXCESSIVE':
      return 'Arterial Transit Travel Delay';
    case 'SLA_PRIORITIZE':
      return 'Priority Queue SLA Escalation';
    case 'STAGGER_LOADING':
      return 'Mixer Departure Staggering';
    case 'TRANSIT_BUFFER':
      return 'Advance Staging Departure Buffer';
    case 'INTRA_ZONE_REALLOCATE':
      return 'Intra-Zone Plant Reallocation';
    default:
      return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
};

export const HomeNeedsAttentionWidget: React.FC<HomeNeedsAttentionWidgetProps> = ({
  alerts,
  alertsLoading,
  alertsError,
  actions,
  actionsLoading,
  actionsError,
}) => {
  const navigate = useNavigate();
  const totalExceptions = alerts.length + actions.length;

  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden flex flex-col justify-between h-full transition-all">
      {/* Top Banner with High-Contrast Header */}
      <div>
        <div className="px-5 py-4 bg-gradient-to-r from-red-50/80 via-white to-amber-50/50 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-red-600 text-white flex items-center justify-center shadow-xs">
              <Flame className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-black text-slate-900 tracking-tight">
                  Operational Triage Feed
                </h2>
                <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-red-100 text-red-800 border border-red-200 animate-pulse">
                  {totalExceptions} Actionable
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                Real-time bottleneck alerts &amp; pending supervisor authorizations
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/alerts')}
            className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 hover:underline"
          >
            Full Console <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Feed Content */}
        <div className="p-5 space-y-5">
          {/* Sub-feed 1: SLA Exception Stream */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Bell className="w-3.5 h-3.5 text-red-500" /> Active SLA Violations
              </span>
              <span className="text-[10px] font-mono font-medium text-slate-400">
                Sorted by highest delay overrun
              </span>
            </div>

            {alertsLoading ? (
              <div className="space-y-2 py-1">
                <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
                <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
              </div>
            ) : alertsError ? (
              <div className="p-3.5 rounded-xl text-xs bg-slate-50 border border-slate-200 text-slate-500">
                Unable to load critical alerts right now.
              </div>
            ) : alerts.length === 0 ? (
              <div className="p-4 rounded-xl text-xs flex items-center gap-2.5 bg-emerald-50/80 border border-emerald-200 text-emerald-900 font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Zero active SLA exception breaches across batch queues and customer drop-offs.</span>
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.slice(0, 3).map((item, idx) => (
                  <div
                    key={item.id}
                    onClick={() => navigate('/alerts')}
                    className="p-3 rounded-xl bg-slate-50/80 hover:bg-red-50/40 border border-slate-200/80 hover:border-red-300 transition cursor-pointer flex items-center justify-between gap-3 group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-red-100 border border-red-200 text-red-700 flex items-center justify-center font-bold text-xs shrink-0">
                        {idx + 1}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900 group-hover:text-red-700 transition">
                            {formatExceptionType(item.alert_type)}
                          </span>
                          <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-white border border-slate-200 text-slate-600">
                            {item.plant_id ? item.plant_id.replace('ACC_', '') : 'VASCO'}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 truncate mt-0.5">
                          {item.message || item.business_impact || 'Exceeded governed operational threshold'}
                        </p>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      {item.actual_value !== undefined && (
                        <div className="text-xs font-black text-red-700 bg-white px-2 py-1 rounded-lg border border-red-200 shadow-2xs font-mono">
                          +{item.actual_value} {item.unit || 'mins'}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sub-feed 2: Directives Requiring Authorization */}
          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-indigo-500" /> Directives Requiring Dispatcher Sign-off
              </span>
              <button
                type="button"
                onClick={() => navigate('/control-tower-actions')}
                className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-0.5 hover:underline"
              >
                Action Center <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {actionsLoading ? (
              <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
            ) : actionsError ? (
              <div className="p-3.5 rounded-xl text-xs bg-slate-50 border border-slate-200 text-slate-500">
                Unable to load pending actions right now.
              </div>
            ) : actions.length === 0 ? (
              <div className="p-4 rounded-xl text-xs text-center bg-slate-50/80 border border-slate-200 text-slate-500 font-medium">
                No recommendations pending supervisor authorization.
              </div>
            ) : (
              <div className="space-y-2">
                {actions.slice(0, 2).map((action) => (
                  <div
                    key={action.action_id}
                    onClick={() => navigate('/control-tower-actions')}
                    className="p-3 rounded-xl bg-indigo-50/40 hover:bg-indigo-50/80 border border-indigo-200/80 hover:border-indigo-300 transition cursor-pointer flex items-center justify-between gap-3 group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-indigo-100 border border-indigo-200 text-indigo-700 flex items-center justify-center shrink-0">
                        <Zap className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900 group-hover:text-indigo-700 transition">
                            {formatExceptionType(action.action_type)}
                          </span>
                          <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-white border border-indigo-200 text-indigo-700">
                            {action.plant_code}
                          </span>
                        </div>
                        {action.predicted_risk_exposure_inr !== undefined && action.predicted_risk_exposure_inr !== null && (
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            Mitigates Potential Loss: <strong className="text-emerald-700 font-mono">₹{Math.round(Number(action.predicted_risk_exposure_inr)).toLocaleString('en-IN')}</strong>
                          </p>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[11px] shadow-2xs transition inline-flex items-center gap-1 shrink-0"
                    >
                      Authorize <ArrowUpRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Status Bar */}
      <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Continuous ML Triage Active</span>
        </span>
        <span className="font-semibold text-slate-700">30s Auto-Refresh</span>
      </div>
    </div>
  );
};
