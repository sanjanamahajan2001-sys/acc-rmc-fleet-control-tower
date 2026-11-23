import React from 'react';
import { TrendingUp, DollarSign, Fuel } from 'lucide-react';
import { IconRupeeCoin, IconBatchingPlantFactory, IconUserGroup } from '../../../components/icons/LinealColorIcons';
import { KPICard } from '../../../components/common/KPICard';

export interface FinancialExposureSummary {
  total_financial_exposure_inr?: number;
  holding_delay_cost_inr?: number;
  retention_sla_penalty_inr?: number;
  idle_fuel_waste_inr?: number;
  total_penalty_mins?: number;
}

export interface FinancialBreakdownItem {
  category: 'PLANT_HOLDING' | 'CUSTOMER_RETENTION' | 'IDLE_FUEL';
  label: string;
  total_cost_inr: number;
  percentage: number;
  penalty_mins: number;
  cost_rate_per_min: number;
}

export interface EntityRiskItem {
  entity_code: string;
  entity_name: string;
  financial_exposure_inr: number;
  penalty_mins: number;
  percentage_of_total?: number;
}

export interface OperationalFinancialExposureData {
  summary: FinancialExposureSummary;
  breakdown: FinancialBreakdownItem[];
  top_plant_risk: EntityRiskItem[];
  top_customer_risk: EntityRiskItem[];
  calculation_status: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculation_notes: string;
}

interface OperationalFinancialExposureSectionProps {
  data: OperationalFinancialExposureData | null;
}

export const OperationalFinancialExposureSection: React.FC<OperationalFinancialExposureSectionProps> = ({ data }) => {
  if (!data || !data.summary) return null;

  const {
    summary,
    breakdown = [],
    top_plant_risk = [],
    top_customer_risk = [],
  } = data;

  const formatINR = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(Number(val))) return '₹0';
    return `₹${Number(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const formatMins = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(Number(val))) return '0m';
    return `${Number(val).toLocaleString('en-IN')}m`;
  };

  const totalExposure = summary.total_financial_exposure_inr ?? 0;

  return (
    <div className="space-y-5">
      {/* 1. Financial Summary Ribbon: 5 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard
          title="Total Financial Exposure"
          value={formatINR(summary.total_financial_exposure_inr)}
          change={totalExposure > 0 ? 'Exposure Active' : 'Zero Exposure'}
          changeType={totalExposure > 0 ? 'negative' : 'positive'}
          subtitle="Quantified Delay & SLA Loss"
        />
        <KPICard
          title="Plant Holding Loss"
          value={formatINR(summary.holding_delay_cost_inr)}
          change="Rate: ₹25/min"
          changeType="negative"
          subtitle="Excess Queue Holding Cost"
        />
        <KPICard
          title="Customer SLA Penalty"
          value={formatINR(summary.retention_sla_penalty_inr)}
          change="Rate: ₹35/min"
          changeType="negative"
          subtitle="Customer Site Retention SLA"
        />
        <KPICard
          title="Idle Fuel Waste"
          value={formatINR(summary.idle_fuel_waste_inr)}
          change="Rate: ₹15/min"
          changeType="neutral"
          subtitle="Mixer Truck Engine Idle Waste"
        />
        <KPICard
          title="Total Penalty Minutes"
          value={formatMins(summary.total_penalty_mins)}
          change="Excess Delay"
          changeType="negative"
          subtitle="Holding + Retention Excess"
        />
      </div>

      {/* 2. Middle Grid: Cost Breakdown & Top Plant Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Cost Category Breakdown */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconRupeeCoin className="w-4 h-4" /> Quantified Cost Breakdown
            </h3>
            <span className="text-xs font-mono font-bold text-slate-900">
              Total: {formatINR(summary.total_financial_exposure_inr)}
            </span>
          </div>

          <div className="space-y-3">
            {breakdown.map((item) => (
              <div key={item.category} className="space-y-2 p-3.5 rounded-md border border-slate-200/80 bg-slate-50">
                <div className="flex justify-between items-center text-xs font-bold">
                  <div className="flex items-center gap-2 text-slate-900">
                    {item.category === 'PLANT_HOLDING' ? (
                      <DollarSign className="w-3.5 h-3.5 text-amber-700" />
                    ) : item.category === 'CUSTOMER_RETENTION' ? (
                      <TrendingUp className="w-3.5 h-3.5 text-rose-700" />
                    ) : (
                      <Fuel className="w-3.5 h-3.5 text-blue-700" />
                    )}
                    <span>{item.label}</span>
                  </div>
                  <div className="font-mono text-sm text-slate-900">
                    <strong>{formatINR(item.total_cost_inr)}</strong> ({item.percentage}%)
                  </div>
                </div>
                <div className="w-full rounded-full h-2 overflow-hidden bg-slate-200">
                  <div
                    className={`h-full rounded-full transition-all ${
                      item.category === 'PLANT_HOLDING'
                        ? 'bg-amber-500'
                        : item.category === 'CUSTOMER_RETENTION'
                        ? 'bg-rose-600'
                        : 'bg-blue-600'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, item.percentage))}%` }}
                  />
                </div>
                <div className="flex justify-between text-[11px] font-mono pt-0.5 text-slate-500">
                  <span>Penalty: <strong className="text-slate-900">{item.penalty_mins}m</strong></span>
                  <span>Rate: <strong className="text-slate-900">₹{item.cost_rate_per_min}/min</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Plant Financial Risk Concentration */}
        <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconBatchingPlantFactory className="w-4 h-4" /> Plant Exposure Concentration
            </h3>
            <span className="text-[11px] font-mono font-medium text-slate-500">
              {top_plant_risk.length} Plants Analyzed
            </span>
          </div>

          <div className="space-y-2.5">
            {top_plant_risk.length === 0 ? (
              <div className="text-xs italic py-6 text-center text-slate-400">Zero plant financial risk detected</div>
            ) : (
              top_plant_risk.map((p) => {
                const sharePct = totalExposure > 0 ? ((p.financial_exposure_inr / totalExposure) * 100).toFixed(1) : '0.0';
                return (
                  <div key={p.entity_code} className="flex items-center justify-between p-3 rounded-md border border-slate-200/80 bg-slate-50 text-xs">
                    <div className="space-y-0.5">
                      <span className="font-bold font-mono text-sm text-slate-900">{p.entity_name}</span>
                      <div className="text-[11px] font-mono text-slate-500">
                        Penalty Duration: <strong className="text-slate-900">{p.penalty_mins} mins</strong>
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="text-sm font-bold text-rose-700">{formatINR(p.financial_exposure_inr)}</div>
                      <div className="text-[11px] text-slate-500">{sharePct}% share</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 3. Customer Financial Risk Concentration */}
      <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
            <IconUserGroup className="w-4 h-4" /> Customer Site SLA Exposure Concentration
          </h3>
          <span className="text-[11px] font-mono font-medium text-slate-500">
            {top_customer_risk.length} Accounts Impacted
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {top_customer_risk.length === 0 ? (
            <div className="col-span-full text-xs italic py-6 text-center text-slate-400">Zero customer financial risk</div>
          ) : (
            top_customer_risk.map((c) => {
              const custSharePct = totalExposure > 0 ? ((c.financial_exposure_inr / totalExposure) * 100).toFixed(1) : '0.0';
              return (
                <div key={c.entity_code} className="p-3.5 rounded-md border border-slate-200/80 bg-slate-50 space-y-1.5">
                  <div className="flex justify-between items-start">
                    <span className="font-bold font-mono text-xs truncate max-w-[180px] text-slate-900">{c.entity_name}</span>
                    <span className="text-xs font-bold font-mono text-rose-700">{formatINR(c.financial_exposure_inr)}</span>
                  </div>
                  <div className="flex justify-between text-[11px] font-mono pt-1 border-t border-slate-200/80 text-slate-500">
                    <span>Excess Time: <strong className="text-slate-900">{c.penalty_mins}m</strong></span>
                    <span>Share: <strong className="text-slate-900">{custSharePct}%</strong></span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
