import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, ChevronLeft, ChevronRight, Gauge, Clock, TrendingUp } from 'lucide-react';
import { IconBatchingPlantFactory, IconUserGroup } from '../../../components/icons/LinealColorIcons';
import { KPICard } from '../../../components/common/KPICard';

export interface FleetEfficiencySummary {
  overall_efficiency_index: number;
  fleet_utilization_pct: number;
  active_vehicles_count?: number;
  total_dispatches?: number;
  avg_turnaround_time_mins: number;
  turnaround_efficiency_pct: number;
  site_unloading_efficiency_pct: number;
}

export interface PlantEfficiencyItem {
  plant_code: string;
  plant_name: string;
  active_vehicles: number;
  total_dispatches: number;
  avg_holding_mins: number;
  turnaround_efficiency_pct: number;
  efficiency_grade: string;
}

export interface CustomerEfficiencyItem {
  customer_code: string;
  customer_name: string;
  total_trips: number;
  avg_retention_mins: number;
  cei_score: number;
  efficiency_grade: string;
}

export interface OperationalFleetEfficiencyData {
  summary: FleetEfficiencySummary;
  plant_efficiency: PlantEfficiencyItem[];
  customer_efficiency: CustomerEfficiencyItem[];
  calculation_status: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculation_notes: string;
}

interface OperationalFleetEfficiencySectionProps {
  data: OperationalFleetEfficiencyData | null;
}

export const OperationalFleetEfficiencySection: React.FC<OperationalFleetEfficiencySectionProps> = ({ data }) => {
  const [custPage, setCustPage] = useState(1);
  const itemsPerPage = 5;

  if (!data || !data.summary) return null;

  const { summary, plant_efficiency = [], customer_efficiency = [] } = data;

  const getGradeBadge = (grade: string) => {
    const isGood = grade.toLowerCase().includes('good') || grade === 'A' || grade === 'B';
    const isWarn = grade.toLowerCase().includes('need') || grade === 'C';

    if (isGood) {
      return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border bg-emerald-50 border-emerald-200 text-emerald-700">Optimal Target</span>;
    }
    if (isWarn) {
      return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border bg-amber-50 border-amber-200 text-amber-700">Attention Required</span>;
    }
    return <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border bg-rose-50 border-rose-200 text-rose-700">SLA Overrun</span>;
  };

  const totalCustPages = Math.ceil(customer_efficiency.length / itemsPerPage) || 1;
  const currentCustItems = customer_efficiency.slice((custPage - 1) * itemsPerPage, custPage * itemsPerPage);

  const activeMixers = summary.active_vehicles_count ?? 'All';

  return (
    <div className="space-y-5">
      {/* 1. Fleet Efficiency Summary Ribbon: 5 KPI Cards with Non-Technical Context */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard
          title="Overall Operational Index"
          value={`${summary.overall_efficiency_index}/100`}
          change={summary.overall_efficiency_index >= 70 ? 'Optimal Operations' : 'Action Required'}
          changeType={summary.overall_efficiency_index >= 70 ? 'positive' : 'negative'}
          subtitle="Composite Plant & Fleet Score"
        />
        <KPICard
          title="Fleet Utilization"
          value={`${summary.fleet_utilization_pct}%`}
          change="Asset Active Ratio"
          changeType={summary.fleet_utilization_pct >= 80 ? 'positive' : 'neutral'}
          subtitle="Active Mixer Trucks in Service"
        />
        <KPICard
          title="Avg Trip Turnaround"
          value={`${summary.avg_turnaround_time_mins}m`}
          change="Cycle Duration"
          changeType="neutral"
          subtitle="Loading + Transit + Site Unload"
        />
        <KPICard
          title="Plant Loading Rating"
          value={`${summary.turnaround_efficiency_pct}%`}
          change="Queue Adherence"
          changeType={summary.turnaround_efficiency_pct >= 70 ? 'positive' : 'negative'}
          subtitle="Baseline SLA: <20m Queue"
        />
        <KPICard
          title="Site Unloading Rating"
          value={`${summary.site_unloading_efficiency_pct}%`}
          change="Discharge Adherence"
          changeType={summary.site_unloading_efficiency_pct >= 70 ? 'positive' : 'negative'}
          subtitle="Baseline SLA: <10m Discharge"
        />
      </div>

      {/* 2. Middle Grid: Plant Turnaround & Customer CEI with Real Delay Financials */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Plant Turnaround Efficiency */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconBatchingPlantFactory className="w-4 h-4" /> Plant Loading Queue &amp; Cost Impact
            </h3>
            <span className="text-[11px] font-mono font-medium text-slate-500">
              {plant_efficiency.length} Plants Ranked
            </span>
          </div>

          <div className="space-y-2.5">
            {plant_efficiency.length === 0 ? (
              <div className="text-xs italic py-6 text-center text-slate-400">Zero plant dispatch activity</div>
            ) : (
              plant_efficiency.map((p) => {
                const excessQueue = Math.max(0, p.avg_holding_mins - 20);
                const holdingPenaltyPerTrip = Math.round(excessQueue * 25);

                return (
                  <div key={p.plant_code} className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-md border border-slate-200/80 bg-slate-50 text-xs gap-2">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold font-mono text-sm text-slate-900">{p.plant_name}</span>
                        {getGradeBadge(p.efficiency_grade)}
                      </div>
                      <div className="text-[11px] font-mono text-slate-500">
                        Active TMs: <strong className="text-slate-900">{p.active_vehicles}</strong> • Total Dispatches: <strong className="text-slate-900">{p.total_dispatches}</strong>
                      </div>
                    </div>
                    <div className="text-left sm:text-right font-mono border-t sm:border-t-0 pt-1.5 sm:pt-0 border-slate-200">
                      <div className={`text-sm font-bold ${excessQueue > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                        Avg Queue: {p.avg_holding_mins}m {excessQueue > 0 ? `(+${excessQueue.toFixed(1)}m excess)` : '(Optimal)'}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {excessQueue > 0 ? `Queue Cost: ~₹${holdingPenaltyPerTrip}/batch` : 'Zero excess queue cost'}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Customer Efficiency Index (CEI Authority) */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 flex flex-col justify-between bg-white shadow-xs">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-1 pb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
                <IconUserGroup className="w-4 h-4" /> Customer Site Unloading Efficiency &amp; Retention
              </h3>
              <span className="text-[11px] font-mono font-bold text-slate-500">
                {customer_efficiency.length} Customer Sites Total
              </span>
            </div>

            <div className="space-y-2.5 mt-3">
              {customer_efficiency.length === 0 ? (
                <div className="text-xs italic py-6 text-center text-slate-400">Zero customer delivery records</div>
              ) : (
                currentCustItems.map((c) => {
                  const excessSiteMins = Math.max(0, c.avg_retention_mins - 10);
                  const sitePenaltyPerTrip = Math.round(excessSiteMins * 35);

                  return (
                    <div key={c.customer_code} className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-md border border-slate-200/80 bg-slate-50 text-xs gap-2">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold font-mono text-sm truncate max-w-[220px] text-slate-900">{c.customer_name}</span>
                          {getGradeBadge(c.efficiency_grade)}
                        </div>
                        <div className="text-[11px] font-mono text-slate-500">
                          Delivered Trips: <strong className="text-slate-900">{c.total_trips}</strong>
                        </div>
                      </div>
                      <div className="text-left sm:text-right font-mono border-t sm:border-t-0 pt-1.5 sm:pt-0 border-slate-200">
                        <div className={`text-sm font-bold ${excessSiteMins > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                          Avg Site Time: {c.avg_retention_mins}m {excessSiteMins > 0 ? `(+${excessSiteMins.toFixed(1)}m delay)` : '(On Time)'}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {excessSiteMins > 0 ? `Site SLA Loss: ~₹${sitePenaltyPerTrip}/trip` : 'Within 10m unloading SLA'}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Pagination Controls */}
          {customer_efficiency.length > itemsPerPage && (
            <div className="flex items-center justify-between pt-3 border-t border-slate-200/80 text-xs font-mono text-slate-500">
              <span>
                Page <strong className="text-slate-900">{custPage}</strong> of <strong className="text-slate-900">{totalCustPages}</strong>
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCustPage((prev) => Math.max(1, prev - 1))}
                  disabled={custPage === 1}
                  className="px-2.5 py-1 rounded-md border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition font-bold bg-white text-slate-700 hover:bg-slate-50"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Prev</span>
                </button>
                <button
                  onClick={() => setCustPage((prev) => Math.min(totalCustPages, prev + 1))}
                  disabled={custPage === totalCustPages}
                  className="px-2.5 py-1 rounded-md border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition font-bold bg-white text-slate-700 hover:bg-slate-50"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
