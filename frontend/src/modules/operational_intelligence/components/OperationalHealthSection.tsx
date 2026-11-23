import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, Gauge } from 'lucide-react';
import { IconShieldSecure } from '../../../components/icons/LinealColorIcons';
import { KPICard } from '../../../components/common/KPICard';

export interface HealthMetric {
  key: string;
  label: string;
  current_value: number;
  unit: string;
  status: string;
  target?: number;
  threshold?: number;
  variance?: number;
  provenance_table: string;
  provenance_formula: string;
}

export interface DatasetFreshness {
  dataset_id: string;
  operational_date: string;
  import_timestamp: string;
  dataset_status: string;
  total_dispatches: number;
  total_trips: number;
}

export interface OperationalHealthData {
  overall_health_score?: number | null;
  health_status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'UNAVAILABLE';
  freshness: DatasetFreshness;
  metrics: HealthMetric[];
  calculation_status: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculation_notes: string;
}

interface OperationalHealthSectionProps {
  data: OperationalHealthData | null;
}

export const OperationalHealthSection: React.FC<OperationalHealthSectionProps> = ({ data }) => {
  if (!data || !data.metrics) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'HEALTHY':
      case 'OPTIMAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border bg-emerald-50 border-emerald-200 text-emerald-700">
            <CheckCircle2 className="w-3.5 h-3.5" /> Optimal Target
          </span>
        );
      case 'DEGRADED':
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border bg-amber-50 border-amber-200 text-amber-700">
            <AlertTriangle className="w-3.5 h-3.5" /> Attention Required
          </span>
        );
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border bg-rose-50 border-rose-200 text-rose-700">
            <XCircle className="w-3.5 h-3.5" /> Critical Breach
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border bg-slate-50 border-slate-200 text-slate-700">
            <HelpCircle className="w-3.5 h-3.5" /> No Data
          </span>
        );
    }
  };

  const getChangeType = (status: string): 'positive' | 'negative' | 'neutral' => {
    if (status === 'OPTIMAL' || status === 'HEALTHY') return 'positive';
    if (status === 'CRITICAL' || status === 'WARNING' || status === 'DEGRADED') return 'negative';
    return 'neutral';
  };

  const healthScore = data.overall_health_score ?? 0;
  const totalDispatches = data.freshness?.total_dispatches ?? 0;
  const totalTrips = data.freshness?.total_trips ?? 0;

  return (
    <div className="space-y-4">
      {/* Top Banner: Executive Health Status & Health Meter */}
      <div className="border border-slate-200/90 rounded-lg p-5 flex flex-col md:flex-row md:items-center justify-between gap-5 shadow-xs bg-white">
        <div className="flex items-center gap-4">
          <div className="shrink-0 flex items-center justify-center">
            <IconShieldSecure className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Operational Dispatch Health Index</span>
              {getStatusBadge(data.health_status)}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono tabular-nums tracking-tight text-slate-900">
                {data.overall_health_score !== undefined && data.overall_health_score !== null
                  ? `${data.overall_health_score}%`
                  : 'N/A'}
              </span>
              <span className="text-xs font-medium text-slate-500">
                SLA Compliance Rate ({totalDispatches.toLocaleString('en-IN')} Canonical Dispatches)
              </span>
            </div>
          </div>
        </div>

        {/* Health Score Gauge / Visual Progress Bar */}
        <div className="w-full md:w-72 space-y-1.5 p-3 rounded-md border border-slate-200 bg-slate-50">
          <div className="flex justify-between text-xs font-bold">
            <span className="flex items-center gap-1.5 text-slate-800">
              <Gauge className="w-3.5 h-3.5 text-blue-700" /> System Score
            </span>
            <span className={`font-mono ${healthScore >= 80 ? 'text-emerald-700' : healthScore >= 60 ? 'text-amber-700' : 'text-rose-700'}`}>
              {healthScore >= 80 ? 'Healthy' : healthScore >= 60 ? 'Degraded' : 'At Risk'}
            </span>
          </div>
          <div className="w-full rounded-full h-2 overflow-hidden bg-slate-200">
            <div
              className={`h-full rounded-full transition-all ${
                healthScore >= 80 ? 'bg-emerald-600' : healthScore >= 60 ? 'bg-amber-500' : 'bg-rose-600'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, healthScore))}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] font-mono font-medium text-slate-500">
            <span>Target: &gt;90% SLA</span>
            <span>Trips: {totalTrips.toLocaleString('en-IN')}</span>
          </div>
        </div>
      </div>

      {/* Grid of Health KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {data.metrics.map((m) => (
          <div key={m.key} className="flex flex-col h-full">
            <KPICard
              title={m.label}
              value={`${m.current_value} ${m.unit}`}
              change={m.status === 'OPTIMAL' ? 'Within SLA' : m.status === 'DEGRADED' ? 'SLA Alert' : m.status === 'CRITICAL' ? 'Breached' : m.status}
              changeType={getChangeType(m.status)}
              subtitle={m.target !== undefined ? `Target: ${m.target} ${m.unit}` : undefined}
            />
          </div>
        ))}
      </div>
    </div>
  );
};
