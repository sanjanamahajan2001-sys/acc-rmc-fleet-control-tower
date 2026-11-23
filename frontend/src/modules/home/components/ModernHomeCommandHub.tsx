import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ListChecks,
  Activity,
  Building2,
  Users,
  Cpu,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  ArrowUpRight,
  Clock,
  ShieldCheck,
  Filter,
} from 'lucide-react';
import { CriticalAlertItem, PendingActionItem } from './HomeNeedsAttentionWidget';
import { SiteReadinessItem, ProblemCustomerItem, PredictiveHealthData } from './HomeOperationalPulseWidget';
import {
  IconIncidentSiren,
  IconSupervisorDirectives,
  IconNetworkHealthGraph,
} from '../../../components/icons/LinealColorIcons';

interface ModernHomeCommandHubProps {
  alerts: CriticalAlertItem[];
  alertsLoading: boolean;
  alertsError: boolean;
  actions: PendingActionItem[];
  actionsLoading: boolean;
  actionsError: boolean;
  sites: SiteReadinessItem[];
  sitesLoading: boolean;
  customers: ProblemCustomerItem[];
  customersLoading: boolean;
  predictive: PredictiveHealthData | null;
  predictiveLoading: boolean;
}

const formatExceptionType = (type: string): { label: string; tag: string } => {
  switch (type) {
    case 'PLANT_HOLDING_BOTTLENECK':
      return { label: 'Plant Loading Bottleneck', tag: 'Batch Queue' };
    case 'SITE_RETENTION_EXCESSIVE':
      return { label: 'Site Unloading Overrun', tag: 'Detention' };
    case 'TRANSIT_DELAY_EXCESSIVE':
      return { label: 'Corridor Transit Delay', tag: 'Transit' };
    case 'SLA_PRIORITIZE':
      return { label: 'Priority SLA Escalation', tag: 'Queue' };
    case 'STAGGER_LOADING':
      return { label: 'Stagger Mixer Loading', tag: 'Plant' };
    case 'TRANSIT_BUFFER':
      return { label: 'Advance Staging Buffer', tag: 'Corridor' };
    case 'INTRA_ZONE_REALLOCATE':
      return { label: 'Intra-Zone Reallocation', tag: 'Network' };
    default:
      return {
        label: type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        tag: 'Exception',
      };
  }
};

export const ModernHomeCommandHub: React.FC<ModernHomeCommandHubProps> = ({
  alerts,
  alertsLoading,
  alertsError,
  actions,
  actionsLoading,
  actionsError,
  sites,
  sitesLoading,
  customers,
  customersLoading,
  predictive,
  predictiveLoading,
}) => {
  const navigate = useNavigate();
  const [filterTag, setFilterTag] = useState<string>('ALL');

  const bestSite = sites.length > 0 ? sites[sites.length - 1] : null;
  const lowestSite = sites.length > 0 ? sites[0] : null;

  // Max lost hours for relative progress bar calculation
  const maxCustomerLostHours = Math.max(
    ...customers.map((c) => c.total_lost_hours || (c.holding_penalty_mins || 0) / 60 || 1),
    600
  );

  const filteredAlerts = alerts.filter((a) => {
    if (filterTag === 'ALL') return true;
    if (filterTag === 'PLANT') return a.alert_type.includes('PLANT') || a.alert_type.includes('HOLDING');
    if (filterTag === 'SITE') return a.alert_type.includes('SITE') || a.alert_type.includes('RETENTION');
    if (filterTag === 'TRANSIT') return a.alert_type.includes('TRANSIT') || a.alert_type.includes('DELAY');
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Quick Filter Bar for Triage */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white px-4 py-2.5 rounded-lg border border-slate-200/90 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-2.5 w-full md:w-auto">
          <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5 shrink-0">
            <Filter className="w-3.5 h-3.5 text-blue-700" /> Filter Stream:
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'ALL', label: `All Exceptions (${alerts.length})` },
              { id: 'PLANT', label: 'Plant Queue' },
              { id: 'SITE', label: 'Site Unloading' },
              { id: 'TRANSIT', label: 'Transit Corridor' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterTag(tab.id)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold whitespace-nowrap transition-all ${
                  filterTag === tab.id
                    ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-2xs'
                    : 'bg-slate-100 hover:bg-slate-200/80 text-slate-700 border border-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-semibold text-slate-500 pt-0.5 sm:pt-0">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
            Live Dispatch Feed Synchronized
          </span>
        </div>
      </div>

      {/* 3-Column Modern Command Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        {/* ======================================================== */}
        {/* COLUMN 1: LIVE SLA EXCEPTION INCIDENT FEED (5 Cols / 42%) */}
        {/* ======================================================== */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-lg shadow-2xs p-4 flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="shrink-0 flex items-center justify-center">
                  <IconIncidentSiren className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">Active SLA Breach Queue</h3>
                  <p className="text-[11px] text-slate-500 font-medium">Sorted by highest operational overrun</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/alerts')}
                className="text-[11px] font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1 hover:underline"
              >
                Alert Console <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {alertsLoading ? (
              <div className="space-y-2 py-3">
                <div className="h-12 animate-pulse rounded-md bg-slate-100" />
                <div className="h-12 animate-pulse rounded-md bg-slate-100" />
                <div className="h-12 animate-pulse rounded-md bg-slate-100" />
              </div>
            ) : alertsError ? (
              <div className="p-3 rounded-md text-xs bg-slate-50 border border-slate-200 text-slate-500 mt-3">
                Unable to load live SLA exceptions.
              </div>
            ) : filteredAlerts.length === 0 ? (
              <div className="p-4 text-center my-3 rounded-md bg-emerald-50/80 border border-emerald-200 text-emerald-900 text-xs font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-700 mx-auto mb-1" />
                <span>Zero active SLA exception breaches matching active filter.</span>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 mt-1">
                {filteredAlerts.slice(0, 4).map((item, idx) => {
                  const meta = formatExceptionType(item.alert_type);
                  return (
                    <div
                      key={item.id}
                      onClick={() => navigate('/alerts')}
                      className="py-2.5 px-2 rounded-md transition hover:bg-slate-50 cursor-pointer flex items-center justify-between gap-3 group"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-6 h-6 rounded bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0 font-mono">
                          {idx + 1}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs font-bold text-slate-900 group-hover:text-blue-700 transition">
                              {meta.label}
                            </span>
                            <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 border border-slate-200 text-slate-700 font-mono">
                              {item.plant_id ? item.plant_id.replace('ACC_', '') : 'NETWORK'}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">
                            {item.message || item.business_impact || 'Exceeded governed operational threshold'}
                          </p>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        {item.actual_value !== undefined && (
                          <div className="text-xs font-bold text-rose-800 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 font-mono tabular-nums">
                            +{item.actual_value} {item.unit || 'mins'}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Critical Triage Queue Active</span>
            <span className="font-semibold text-slate-700">30s Live Sync</span>
          </div>
        </div>

        {/* ======================================================== */}
        {/* COLUMN 2: SUPERVISOR AUTHORIZATION DIRECTIVES (4 Cols / 33%) */}
        {/* ======================================================== */}
        <div className="lg:col-span-4 bg-white border border-slate-200/90 rounded-lg shadow-2xs p-4 flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="shrink-0 flex items-center justify-center">
                  <IconSupervisorDirectives className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">Supervisor Directives</h3>
                  <p className="text-[11px] text-slate-500 font-medium">Authorizations to unlock savings</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/control-tower-actions')}
                className="text-[11px] font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1 hover:underline"
              >
                Action Hub <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {actionsLoading ? (
              <div className="space-y-2 py-3">
                <div className="h-14 animate-pulse rounded-md bg-slate-100" />
                <div className="h-14 animate-pulse rounded-md bg-slate-100" />
              </div>
            ) : actionsError ? (
              <div className="p-3 rounded-md text-xs bg-slate-50 border border-slate-200 text-slate-500 mt-3">
                Unable to load pending directives.
              </div>
            ) : actions.length === 0 ? (
              <div className="p-4 text-center my-3 rounded-md bg-slate-50 border border-slate-200 text-slate-500 text-xs font-medium">
                No directives pending supervisor authorization.
              </div>
            ) : (
              <div className="space-y-2.5 mt-2.5">
                {actions.slice(0, 3).map((action) => {
                  const meta = formatExceptionType(action.action_type);
                  return (
                    <div
                      key={action.action_id}
                      onClick={() => navigate('/control-tower-actions')}
                      className="p-3 rounded-md bg-slate-50/80 hover:bg-slate-100 border border-slate-200/90 transition cursor-pointer flex flex-col justify-between gap-2 group shadow-2xs"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-900 group-hover:text-blue-700 transition">
                              {meta.label}
                            </span>
                            <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-white border border-slate-200 text-slate-700 font-mono">
                              {action.plant_code}
                            </span>
                          </div>
                          {action.predicted_risk_exposure_inr !== undefined && action.predicted_risk_exposure_inr !== null && (
                            <div className="text-[11px] text-slate-600 mt-1">
                              Avoided Exposure: <strong className="text-emerald-700 font-mono tabular-nums">₹{Math.round(Number(action.predicted_risk_exposure_inr)).toLocaleString('en-IN')}</strong>
                            </div>
                          )}
                        </div>

                        <button
                          type="button"
                          className="px-2.5 py-1 rounded-md bg-blue-700 hover:bg-blue-800 text-white font-semibold text-[10px] shadow-2xs transition inline-flex items-center gap-0.5 shrink-0"
                        >
                          Sign-off <ArrowUpRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Human-In-The-Loop Governance</span>
            <span className="font-semibold text-blue-800">Authorized Access</span>
          </div>
        </div>

        {/* ======================================================== */}
        {/* COLUMN 3: NETWORK READINESS & CHRONIC DETENTION (3 Cols / 25%) */}
        {/* ======================================================== */}
        <div className="lg:col-span-3 bg-white border border-slate-200/90 rounded-lg shadow-2xs p-4 flex flex-col justify-between group">
          <div className="space-y-3.5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="shrink-0 flex items-center justify-center">
                  <IconNetworkHealthGraph className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 tracking-tight">Network Health</h3>
                  <p className="text-[11px] text-slate-500 font-medium">Readiness benchmarks &amp; clients</p>
                </div>
              </div>
            </div>

            {/* Benchmark Split Bar */}
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                Plant SRI Benchmark Split
              </span>
              <div className="grid grid-cols-2 gap-2">
                <div
                  onClick={() => navigate('/site-comparison')}
                  className="p-2.5 rounded-md bg-slate-50 border border-slate-200 cursor-pointer hover:bg-slate-100 transition shadow-2xs"
                >
                  <span className="text-[9px] font-bold text-emerald-800 uppercase block">Leader</span>
                  <div className="font-bold text-xs text-slate-900 truncate">{bestSite?.site_name || 'ACC VASCO'}</div>
                  <div className="text-xs font-bold font-mono text-emerald-700 mt-0.5 tabular-nums">{bestSite?.sri_score ?? '78.2'} SRI</div>
                </div>

                <div
                  onClick={() => navigate('/site-comparison')}
                  className="p-2.5 rounded-md bg-slate-50 border border-slate-200 cursor-pointer hover:bg-slate-100 transition shadow-2xs"
                >
                  <span className="text-[9px] font-bold text-rose-800 uppercase block">Laggard</span>
                  <div className="font-bold text-xs text-slate-900 truncate">{lowestSite?.site_name || 'ACC DHARGA'}</div>
                  <div className="text-xs font-bold font-mono text-rose-700 mt-0.5 tabular-nums">{lowestSite?.sri_score ?? '51.6'} SRI</div>
                </div>
              </div>
            </div>

            {/* Chronic Customer Detention Hotspots (with visual progress fill) */}
            <div className="pt-2.5 border-t border-slate-100">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                Chronic Client Detention Hours
              </span>
              <div className="space-y-1.5">
                {customers.slice(0, 3).map((cust, idx) => {
                  const lostHours = cust.total_lost_hours || (cust.holding_penalty_mins || 0) / 60 || 0;
                  const barWidthPct = Math.min(100, Math.max(15, (lostHours / maxCustomerLostHours) * 100));

                  return (
                    <div
                      key={cust.customer_id || idx}
                      onClick={() => navigate('/overall-dashboard')}
                      className="cursor-pointer group"
                    >
                      <div className="flex items-center justify-between text-xs mb-0.5">
                        <span className="font-bold text-slate-700 truncate max-w-[130px] group-hover:text-blue-700 transition text-[11px]">
                          #{idx + 1} {cust.customer_name || cust.customer_code || 'DEFAULT CUSTOMER'}
                        </span>
                        <span className="font-mono font-bold text-slate-900 text-[11px] tabular-nums">
                          {lostHours.toFixed(1)}h
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden border border-slate-200">
                        <div
                          className="bg-amber-600 h-full rounded-full"
                          style={{ width: `${barWidthPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Model Authority Telemetry Pill */}
            <div className="pt-2.5 border-t border-slate-100">
              <div className="p-2 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between shadow-2xs">
                <div>
                  <span className="text-[9px] text-slate-500 font-bold uppercase block">ML Authority</span>
                  <span className="text-xs font-bold text-slate-900 font-mono">{predictive?.active_authority_version || 'V2.11-LIVE'}</span>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-700 text-white flex items-center gap-1 shadow-2xs">
                  <CheckCircle2 className="w-3 h-3" /> ONLINE
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Model Health: Active</span>
            <span className="font-mono font-bold text-slate-700 tabular-nums">12.0k Predictions</span>
          </div>
        </div>
      </div>
    </div>
  );
};
