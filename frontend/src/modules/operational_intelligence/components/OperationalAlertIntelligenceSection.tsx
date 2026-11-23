import React from 'react';
import { AlertCircle, AlertTriangle, ExternalLink, CheckCircle2 } from 'lucide-react';
import { IconBatchingPlantFactory, IconUserGroup, IconCycleStopwatch } from '../../../components/icons/LinealColorIcons';
import { useNavigate } from 'react-router-dom';
import { KPICard } from '../../../components/common/KPICard';

export interface AlertSummaryCounts {
  total_active?: number;
  open_count?: number;
  acknowledged_count?: number;
  critical_count?: number;
  warning_count?: number;
  info_count?: number;
  // Legacy aliases
  total_unresolved?: number;
  critical_rate_pct?: number;
}

export interface PriorityAlertItem {
  id: string;
  alert_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  status: string;
  plant_id: string;
  customer_id: string;
  detected_at: string;
  actual_value?: number | null;
  threshold_value?: number | null;
  unit?: string | null;
}

export interface ConcentrationItem {
  group_code: string;
  group_name: string;
  critical_count: number;
  warning_count: number;
  total_count: number;
}

export interface OperationalAlertIntelligenceData {
  summary: AlertSummaryCounts;
  priority_alerts: PriorityAlertItem[];
  top_categories: { alert_type: string; label: string; count: number; percentage: number; severity: string }[];
  plant_concentration: ConcentrationItem[];
  customer_concentration: ConcentrationItem[];
  calculation_status: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculation_notes: string;
}

interface OperationalAlertIntelligenceSectionProps {
  data: OperationalAlertIntelligenceData | null;
}

export const OperationalAlertIntelligenceSection: React.FC<OperationalAlertIntelligenceSectionProps> = ({ data }) => {
  const navigate = useNavigate();

  if (!data || !data.summary) return null;

  const { summary, priority_alerts = [], plant_concentration = [], customer_concentration = [] } = data;

  const totalActive = summary.total_active ?? summary.total_unresolved ?? 0;
  const criticalCount = summary.critical_count ?? 0;
  const warningCount = summary.warning_count ?? 0;
  const criticalRatePct = totalActive > 0 ? Math.round((criticalCount / totalActive) * 100) : 0;

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border bg-rose-50 border-rose-200 text-rose-700">
            <AlertCircle className="w-3 h-3" /> Critical
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border bg-amber-50 border-amber-200 text-amber-700">
            <AlertTriangle className="w-3 h-3" /> Warning
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border bg-slate-50 border-slate-200 text-slate-700">
            <CheckCircle2 className="w-3 h-3" /> Info
          </span>
        );
    }
  };

  return (
    <div className="space-y-5">
      {/* 1. Alert Summary Ribbon: 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Active Unresolved Alerts"
          value={totalActive}
          change={totalActive > 0 ? `${criticalCount} Critical Active` : 'Zero Exceptions'}
          changeType={totalActive > 0 ? (criticalCount > 0 ? 'negative' : 'neutral') : 'positive'}
          subtitle="Real-time Dispatch Alerts"
        />
        <KPICard
          title="Critical Alerts (P1)"
          value={criticalCount}
          change={criticalCount > 0 ? 'Requires Immediate Triage' : 'Healthy Queue'}
          changeType={criticalCount > 0 ? 'negative' : 'positive'}
          subtitle="Severe SLA/Transit Delays"
        />
        <KPICard
          title="Warning Alerts (P2)"
          value={warningCount}
          change={warningCount > 0 ? 'Early Warning Level' : 'Zero Warnings'}
          changeType={warningCount > 0 ? 'neutral' : 'positive'}
          subtitle="Threshold Exceeded"
        />
        <KPICard
          title="Critical Severity Ratio"
          value={`${criticalRatePct}%`}
          change={criticalRatePct > 25 ? 'High Critical Ratio' : 'Normal Ratio'}
          changeType={criticalRatePct > 25 ? 'negative' : 'positive'}
          subtitle="Critical vs Total Share"
        />
      </div>

      {/* 2. Operational Concentration Breakdown: Plant vs Customer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Plant Concentration Card */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-3 bg-white shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconBatchingPlantFactory className="w-4 h-4" /> Plant Incident Concentration
            </h3>
            <span className="text-[11px] font-mono font-medium text-slate-500">
              {plant_concentration.length} Plants Active
            </span>
          </div>

          <div className="space-y-2.5">
            {plant_concentration.length === 0 ? (
              <div className="text-xs italic py-6 text-center text-slate-400">Zero active plant alert concentration</div>
            ) : (
              plant_concentration.map((p) => {
                const critPct = p.total_count > 0 ? (p.critical_count / p.total_count) * 100 : 0;
                const warnPct = p.total_count > 0 ? (p.warning_count / p.total_count) * 100 : 0;

                return (
                  <div key={p.group_code} className="p-3 rounded-md border border-slate-200/80 bg-slate-50 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold font-mono text-sm text-slate-900">{p.group_name}</span>
                      <span className="font-bold font-mono px-2 py-0.5 rounded-md border text-[11px] bg-white border-slate-200 text-slate-900">
                        {p.total_count} Incidents Total
                      </span>
                    </div>

                    {/* Proportional Severity Bar */}
                    <div className="w-full h-2 rounded-full overflow-hidden flex bg-slate-200">
                      <div className="bg-rose-600 h-full transition-all" style={{ width: `${critPct}%` }} title={`${p.critical_count} Critical`} />
                      <div className="bg-amber-500 h-full transition-all" style={{ width: `${warnPct}%` }} title={`${p.warning_count} Warning`} />
                    </div>

                    <div className="flex justify-between items-center text-[11px] font-mono">
                      <span className={`font-bold ${p.critical_count > 0 ? 'text-rose-700' : 'text-slate-500'}`}>
                        {p.critical_count} Critical
                      </span>
                      <span className={`font-bold ${p.warning_count > 0 ? 'text-amber-700' : 'text-slate-500'}`}>
                        {p.warning_count} Warning
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Customer Concentration Card */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-3 bg-white shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconUserGroup className="w-4 h-4" /> Customer Incident Concentration
            </h3>
            <span className="text-[11px] font-mono font-medium text-slate-500">
              {customer_concentration.length} Sites Impacted
            </span>
          </div>

          <div className="space-y-2.5">
            {customer_concentration.length === 0 ? (
              <div className="text-xs italic py-6 text-center text-slate-400">Zero active customer alert concentration</div>
            ) : (
              customer_concentration.map((c) => {
                const critPct = c.total_count > 0 ? (c.critical_count / c.total_count) * 100 : 0;
                const warnPct = c.total_count > 0 ? (c.warning_count / c.total_count) * 100 : 0;

                return (
                  <div key={c.group_code} className="p-3 rounded-md border border-slate-200/80 bg-slate-50 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold font-mono text-sm truncate max-w-[240px] text-slate-900">{c.group_name}</span>
                      <span className="font-bold font-mono px-2 py-0.5 rounded-md border text-[11px] shrink-0 bg-white border-slate-200 text-slate-900">
                        {c.total_count} Incidents
                      </span>
                    </div>

                    {/* Proportional Severity Bar */}
                    <div className="w-full h-2 rounded-full overflow-hidden flex bg-slate-200">
                      <div className="bg-rose-600 h-full transition-all" style={{ width: `${critPct}%` }} title={`${c.critical_count} Critical`} />
                      <div className="bg-amber-500 h-full transition-all" style={{ width: `${warnPct}%` }} title={`${c.warning_count} Warning`} />
                    </div>

                    <div className="flex justify-between items-center text-[11px] font-mono">
                      <span className={`font-bold ${c.critical_count > 0 ? 'text-rose-700' : 'text-slate-500'}`}>
                        {c.critical_count} Critical
                      </span>
                      <span className={`font-bold ${c.warning_count > 0 ? 'text-amber-700' : 'text-slate-500'}`}>
                        {c.warning_count} Warning
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 3. Priority Unresolved Alerts Action List */}
      <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconCycleStopwatch className="w-4 h-4" /> Priority Unresolved Exceptions
            </h3>
            <p className="text-[11px] font-medium mt-0.5 text-slate-500">
              Ranked by severity and operational impact for active control tower triage
            </p>
          </div>
          <button
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold border border-slate-200 transition bg-white text-blue-700 hover:bg-slate-50 self-start sm:self-center"
          >
            <span>Open Alert Center</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="space-y-2.5">
          {priority_alerts.length === 0 ? (
            <div className="text-xs italic py-6 text-center text-slate-400">Zero active unresolved alerts</div>
          ) : (
            priority_alerts.map((a) => (
              <div
                key={a.id}
                onClick={() => navigate(`/alerts?alert_id=${a.id}`)}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-md border border-slate-200/80 bg-slate-50 transition cursor-pointer hover:border-blue-400"
              >
                <div className="flex items-start sm:items-center gap-3">
                  {getSeverityBadge(a.severity)}
                  <div>
                    <div className="text-xs font-bold capitalize text-slate-900">
                      {a.alert_type.replace(/_/g, ' ').toLowerCase()}
                    </div>
                    <div className="text-[11px] font-mono flex flex-wrap items-center gap-x-2 gap-y-1 mt-0.5 text-slate-500">
                      <span>Plant: <strong className="text-slate-900">{a.plant_id}</strong></span>
                      <span>•</span>
                      <span>Customer: <strong className="text-slate-900">{a.customer_id}</strong></span>
                      {a.actual_value !== null && a.actual_value !== undefined && (
                        <>
                          <span>•</span>
                          <span>Value: <strong className="text-slate-900">{a.actual_value} {a.unit || ''}</strong></span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-[11px] font-mono shrink-0 self-end sm:self-center text-slate-500">
                  <span className="px-2.5 py-0.5 rounded-md border border-slate-200 bg-white font-bold text-slate-800">
                    {a.status}
                  </span>
                  <span>{new Date(a.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
