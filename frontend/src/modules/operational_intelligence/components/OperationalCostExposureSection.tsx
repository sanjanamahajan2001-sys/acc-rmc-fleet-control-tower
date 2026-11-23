import React, { useState } from 'react';
import { IndianRupee, ChevronLeft, ChevronRight, TrendingDown, Clock, ShieldAlert, AlertTriangle, AlertCircle } from 'lucide-react';
import { IconBatchingPlantFactory, IconUserGroup, IconDatasetDatabase } from '../../../components/icons/LinealColorIcons';
import { KPICard } from '../../../components/common/KPICard';

export interface CostExposureSummary {
  realized_cost_exposure_inr?: number;
  total_realized_exposure_inr?: number;
  predicted_cost_exposure_inr?: number;
  holding_penalty_cost_inr?: number;
  realized_holding_cost_inr?: number;
  retention_sla_penalty_inr?: number;
  realized_retention_sla_penalty_inr?: number;
  idle_fuel_waste_inr?: number;
  realized_idle_fuel_cost_inr?: number;
  high_cost_operations_count?: number;
  avoidable_delay_mins?: number;
  potential_savings_inr?: number;
}

export interface HighCostOperation {
  dispatch_id: string;
  dispatch_code: string;
  plant_code?: string;
  plant_name?: string;
  customer_code?: string;
  customer_name?: string;
  vehicle_id?: string;
  vehicle_code?: string;
  holding_duration_mins?: number;
  holding_penalty_mins?: number;
  holding_cost_inr?: number;
  retention_duration_mins?: number;
  retention_penalty_mins?: number;
  retention_penalty_inr?: number;
  idle_fuel_cost_inr?: number;
  total_exposure_inr?: number;
  total_trip_exposure_inr?: number;
  primary_cost_driver?: string;
  risk_level?: string;
  executed_at?: string;
}

export interface PaginatedHighCostOperations {
  items: HighCostOperation[];
  total_count?: number;
  total_items?: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PlantCostRisk {
  plant_code: string;
  plant_name: string;
  dispatches_count: number;
  total_exposure_inr: number;
  exposure_percentage: number;
}

export interface CustomerCostRisk {
  customer_code: string;
  customer_name: string;
  delivered_trips: number;
  total_exposure_inr: number;
  exposure_percentage: number;
}

export interface OperationalCostExposureData {
  summary: CostExposureSummary;
  high_cost_operations: PaginatedHighCostOperations;
  plant_cost_risk: PlantCostRisk[];
  customer_cost_risk: CustomerCostRisk[];
  calculation_status: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculation_notes: string;
}

interface OperationalCostExposureSectionProps {
  data: OperationalCostExposureData | null;
  onPageChange?: (newPage: number) => void;
}

export const OperationalCostExposureSection: React.FC<OperationalCostExposureSectionProps> = ({
  data,
  onPageChange,
}) => {
  const [currentCustPage, setCustPage] = useState(1);
  const custItemsPerPage = 5;

  if (!data || !data.summary) return null;

  const {
    summary,
    high_cost_operations = { items: [], total_items: 0, page: 1, page_size: 10, total_pages: 1 },
    plant_cost_risk = [],
    customer_cost_risk = [],
  } = data;

  const formatINR = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(Number(val))) return '₹0';
    return `₹${Number(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const totalCost = summary.realized_cost_exposure_inr ?? summary.total_realized_exposure_inr ?? 0;
  const holdingCost = summary.holding_penalty_cost_inr ?? summary.realized_holding_cost_inr ?? 0;
  const retentionPenalty = summary.retention_sla_penalty_inr ?? summary.realized_retention_sla_penalty_inr ?? 0;
  const idleFuelCost = summary.idle_fuel_waste_inr ?? summary.realized_idle_fuel_cost_inr ?? 0;
  const highCostCount = summary.high_cost_operations_count ?? high_cost_operations.total_items ?? high_cost_operations.total_count ?? 0;

  // Realized queue loss is the holding delay + associated idle fuel waste
  const plantQueueCost = holdingCost + idleFuelCost;

  const customerCostRisk = customer_cost_risk || [];
  const totalCustPages = Math.ceil(customerCostRisk.length / custItemsPerPage) || 1;
  const paginatedCustRisk = customerCostRisk.slice(
    (currentCustPage - 1) * custItemsPerPage,
    currentCustPage * custItemsPerPage
  );

  return (
    <div className="space-y-5">
      {/* 1. Operational Cost Audit Banner */}
      <div className="border border-slate-200/90 rounded-lg p-5 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-5 bg-white">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-700">Operational Cost Audit &amp; Loss Breakdown</span>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border bg-emerald-50 border-emerald-200 text-emerald-700">
              PostgreSQL Grounded
            </span>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-2xl md:text-3xl font-bold font-mono tabular-nums tracking-tight text-slate-900">
              {formatINR(totalCost)}
            </span>
            <span className="text-xs font-medium text-slate-500">
              Total Realized Operational Loss (Queue Holding + Site Retention + Idle Fuel)
            </span>
          </div>
        </div>

        {/* 2 Key Cost Driver Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 shrink-0">
          <div className="p-3.5 rounded-md border border-amber-200 bg-amber-50/60 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
              <IconBatchingPlantFactory className="w-3.5 h-3.5" /> Plant Queue Loss (Hold + Fuel)
            </span>
            <div className="text-base font-bold text-slate-900 font-mono">{formatINR(plantQueueCost)}</div>
            <span className="text-[10px] text-slate-500">Holding (₹25/m) + Idle Fuel (₹15/m)</span>
          </div>

          <div className="p-3.5 rounded-md border border-blue-200 bg-blue-50/60 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-blue-800 flex items-center gap-1.5">
              <IconUserGroup className="w-3.5 h-3.5" /> Customer Site SLA Penalties
            </span>
            <div className="text-base font-bold text-slate-900 font-mono">{formatINR(retentionPenalty)}</div>
            <span className="text-[10px] text-slate-500">Site Retention past 10m SLA (₹35/m)</span>
          </div>
        </div>
      </div>

      {/* 2. Realized Financial Impact: 5 KPI Cards with Transparent Cost Formulas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard
          title="Total Financial Loss"
          value={formatINR(totalCost)}
          change={totalCost > 0 ? 'Loss Active' : 'Zero Loss'}
          changeType={totalCost > 0 ? 'negative' : 'positive'}
          subtitle="Sum of All 3 Delay Cost Rates"
        />
        <KPICard
          title="Plant Queue Holding"
          value={formatINR(holdingCost)}
          change="Rate: ₹25/min"
          changeType="negative"
          subtitle="Delay Past 20m Loading SLA"
        />
        <KPICard
          title="Customer Site Overruns"
          value={formatINR(retentionPenalty)}
          change="Rate: ₹35/min"
          changeType="negative"
          subtitle="Delay Past 10m Unloading SLA"
        />
        <KPICard
          title="Mixer Truck Idle Fuel"
          value={formatINR(idleFuelCost)}
          change="Rate: ₹15/min"
          changeType="neutral"
          subtitle="Fuel Burned During Queue Delay"
        />
        <KPICard
          title="High-Cost Dispatches"
          value={highCostCount}
          change={highCostCount > 0 ? `${highCostCount} Outliers Ranked` : 'Zero Outliers'}
          changeType={highCostCount > 0 ? 'negative' : 'positive'}
          subtitle="Dispatches with Excess Overrun"
        />
      </div>

      {/* 3. Top High-Cost Operations Table with Explicit Component Breakdown & Root Cause */}
      <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconDatasetDatabase className="w-4 h-4" /> High-Cost Operation Dispatch Records
            </h3>
            <p className="text-[11px] font-medium mt-0.5 text-slate-500">
              Top delay cost outliers ranked by total realized financial exposure: <span className="font-mono">Total = (Holding × ₹25) + (Retention × ₹35) + (Idle Fuel × ₹15)</span>
            </p>
          </div>
          <span className="text-[11px] font-mono font-bold px-2.5 py-1 rounded-md border border-blue-200 bg-blue-50 text-blue-700 self-start sm:self-center">
            {high_cost_operations.total_items ?? high_cost_operations.total_count ?? 0} Outliers Ranked
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="border-b border-slate-200 font-mono uppercase text-[11px] text-slate-600 bg-slate-50">
              <tr>
                <th className="p-3">Dispatch Code</th>
                <th className="p-3">Plant</th>
                <th className="p-3">Customer</th>
                <th className="p-3 text-right">Plant Queue Loss</th>
                <th className="p-3 text-right">Site Unload Loss</th>
                <th className="p-3 text-right">Idle Fuel Loss</th>
                <th className="p-3 text-right">Total Realized Loss</th>
                <th className="p-3">Primary Root Cause</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {(!high_cost_operations.items || high_cost_operations.items.length === 0) ? (
                <tr>
                  <td colSpan={8} className="p-6 text-center italic text-xs text-slate-400">
                    Zero high-cost operational outliers
                  </td>
                </tr>
              ) : (
                high_cost_operations.items.map((op) => {
                  const holdMins = op.holding_penalty_mins ?? op.holding_duration_mins ?? 0;
                  const retMins = op.retention_penalty_mins ?? op.retention_duration_mins ?? 0;
                  const expInr = op.total_exposure_inr ?? op.total_trip_exposure_inr ?? 0;
                  const plantName = op.plant_name || op.plant_code || 'UNASSIGNED';
                  const custName = op.customer_name || op.customer_code || 'UNASSIGNED';

                  const holdLossInr = Math.round(holdMins * 25);
                  const retLossInr = Math.round(retMins * 35);
                  const fuelLossInr = Math.round(holdMins * 15);

                  // Deterministic, non-simulated operational root cause tag
                  const isPlantBottleneck = (holdLossInr + fuelLossInr) >= retLossInr;

                  return (
                    <tr key={op.dispatch_id} className="transition hover:bg-slate-50/70">
                      <td className="p-3 font-bold text-blue-700">{op.dispatch_code}</td>
                      <td className="p-3 font-sans font-medium text-slate-800">{plantName}</td>
                      <td className="p-3 font-sans font-medium max-w-[170px] truncate text-slate-800">{custName}</td>
                      <td className="p-3 text-right text-slate-800">
                        {formatINR(holdLossInr)} <span className="text-[10px] text-slate-500">({holdMins}m)</span>
                      </td>
                      <td className="p-3 text-right text-slate-800">
                        {formatINR(retLossInr)} <span className="text-[10px] text-slate-500">({retMins}m)</span>
                      </td>
                      <td className="p-3 text-right text-slate-500">
                        {formatINR(fuelLossInr)}
                      </td>
                      <td className="p-3 text-right font-bold text-rose-700">
                        {formatINR(expInr)}
                      </td>
                      <td className="p-3 font-sans">
                        <span
                          className={`px-2.5 py-1 rounded-md text-[11px] font-bold border inline-flex items-center gap-1.5 ${
                            isPlantBottleneck
                              ? 'bg-amber-50 border-amber-200 text-amber-700'
                              : 'bg-blue-50 border-blue-200 text-blue-700'
                          }`}
                        >
                          {isPlantBottleneck ? (
                            <>
                              <IconBatchingPlantFactory className="w-3.5 h-3.5 shrink-0" />
                              <span>Plant Batch Queue ({holdMins}m)</span>
                            </>
                          ) : (
                            <>
                              <IconUserGroup className="w-3.5 h-3.5 shrink-0" />
                              <span>Site Unloading Delay ({retMins}m)</span>
                            </>
                          )}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {high_cost_operations.total_pages > 1 && (
          <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-xs font-mono text-slate-500">
            <span>
              Page <strong className="text-slate-900">{high_cost_operations.page}</strong> of <strong className="text-slate-900">{high_cost_operations.total_pages}</strong>
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onPageChange?.(high_cost_operations.page - 1)}
                disabled={high_cost_operations.page <= 1}
                className="px-2.5 py-1 rounded-md border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition font-bold bg-white text-slate-700 hover:bg-slate-50"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                onClick={() => onPageChange?.(high_cost_operations.page + 1)}
                disabled={high_cost_operations.page >= high_cost_operations.total_pages}
                className="px-2.5 py-1 rounded-md border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition font-bold bg-white text-slate-700 hover:bg-slate-50"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4. Plant and Customer Cost Risk Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Plant Cost Risk Concentration */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconBatchingPlantFactory className="w-4 h-4" /> Plant Batching Queue Cost Leakage
            </h3>
            <span className="text-[11px] font-mono font-medium text-slate-500">
              {plant_cost_risk.length} Plants Ranked
            </span>
          </div>

          <div className="space-y-2.5">
            {plant_cost_risk.length === 0 ? (
              <div className="text-xs italic py-6 text-center text-slate-400">Zero plant cost risk records</div>
            ) : (
              plant_cost_risk.map((p) => (
                <div key={p.plant_code} className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-md border border-slate-200/80 bg-slate-50 text-xs gap-2">
                  <div className="space-y-1">
                    <span className="font-bold font-mono text-sm text-slate-900">{p.plant_name}</span>
                    <div className="text-[11px] font-mono text-slate-500">
                      Dispatches Handled: <strong className="text-slate-900">{p.dispatches_count}</strong>
                    </div>
                  </div>
                  <div className="text-left sm:text-right font-mono border-t sm:border-t-0 pt-1.5 sm:pt-0 border-slate-200">
                    <div className="text-base font-bold text-rose-700">{formatINR(p.total_exposure_inr)}</div>
                    <div className="text-[11px] text-slate-500">Share: {p.exposure_percentage}% of total delay loss</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Customer Cost Risk Concentration */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 flex flex-col justify-between bg-white shadow-xs">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-1 pb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
                <IconUserGroup className="w-4 h-4" /> Customer Site Unloading Overrun Cost
              </h3>
              {customerCostRisk.length > 0 && (
                <span className="text-[11px] font-mono font-bold text-slate-500">
                  {customerCostRisk.length} Customer Accounts
                </span>
              )}
            </div>

            <div className="space-y-2.5 mt-3">
              {customerCostRisk.length === 0 ? (
                <div className="text-xs italic py-6 text-center text-slate-400">Zero customer cost risk records</div>
              ) : (
                paginatedCustRisk.map((c) => (
                  <div key={c.customer_code} className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-md border border-slate-200/80 bg-slate-50 text-xs gap-2">
                    <div className="space-y-1">
                      <span className="font-bold font-mono text-sm truncate max-w-[220px] text-slate-900">{c.customer_name}</span>
                      <div className="text-[11px] font-mono text-slate-500">
                        Delivered Trips: <strong className="text-slate-900">{c.delivered_trips}</strong>
                      </div>
                    </div>
                    <div className="text-left sm:text-right font-mono border-t sm:border-t-0 pt-1.5 sm:pt-0 border-slate-200">
                      <div className="text-base font-bold text-amber-700">{formatINR(c.total_exposure_inr)}</div>
                      <div className="text-[11px] text-slate-500">Share: {c.exposure_percentage}% of total delay loss</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Customer Risk Pagination Controls */}
          {totalCustPages > 1 && (
            <div className="flex items-center justify-between pt-3 mt-2 border-t border-slate-200 text-xs font-mono text-slate-500">
              <span>
                Page <strong className="text-slate-900">{currentCustPage}</strong> of <strong className="text-slate-900">{totalCustPages}</strong>
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCustPage((p) => Math.max(1, p - 1))}
                  disabled={currentCustPage <= 1}
                  className="px-2.5 py-1 rounded-md border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition font-bold bg-white text-slate-700 hover:bg-slate-50"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Prev</span>
                </button>
                <button
                  onClick={() => setCustPage((p) => Math.min(totalCustPages, p + 1))}
                  disabled={currentCustPage >= totalCustPages}
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
