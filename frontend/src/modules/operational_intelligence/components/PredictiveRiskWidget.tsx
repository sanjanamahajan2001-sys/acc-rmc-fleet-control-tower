import React from 'react';
import { AlertTriangle, Clock, ShieldAlert, Truck, Building } from 'lucide-react';
import { OperationalPredictionItem, ModelAuthorityItem } from '../pages/PredictiveIntelligencePage';

interface PredictiveRiskWidgetProps {
  prediction?: OperationalPredictionItem;
  snapshot?: OperationalPredictionItem;
  model?: ModelAuthorityItem;
  className?: string;
}

/**
 * PredictiveRiskWidget Component
 * Non-technical presentation layer rendering operational risk forecasts and concrete delay actions.
 */
export const PredictiveRiskWidget: React.FC<PredictiveRiskWidgetProps> = ({ prediction, snapshot, model, className = '' }) => {
  const target = prediction || snapshot || (model as any);
  if (!target) return null;

  const model_name = target.model_name;
  const predicted_value = target.predicted_value;
  const financial_exposure_inr = target.financial_exposure_inr;
  const sla_penalty_risk_inr = target.sla_penalty_risk_inr;
  const prediction_outputs = target.prediction_outputs;

  // Render Plant Turnaround Forecaster
  if (model_name === 'turnaround_regressor') {
    const turnaroundMins = predicted_value ?? prediction_outputs?.predicted_avg_turnaround_mins ?? 0;
    const staggerMins = prediction_outputs?.recommended_stagger_mins ?? (turnaroundMins > 25 ? Math.round(turnaroundMins - 20) : 0);
    return (
      <div
        className={`p-3.5 rounded-md border border-amber-300 bg-amber-50/70 text-amber-900 space-y-2 shadow-2xs ${className}`}
        data-testid="staggered-loading-card"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Building className="w-4 h-4 text-amber-700" />
            <span className="font-bold text-xs uppercase tracking-wider text-amber-900">Plant Loading Queue Forecast</span>
          </div>
          <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md border bg-white border-amber-300 text-amber-800 tabular-nums">
            {turnaroundMins.toFixed(1)}m Estimated Queue
          </span>
        </div>
        <p className="text-xs font-medium text-slate-800">
          {staggerMins > 0
            ? `Recommended Action: Space next truck arrival by +${staggerMins} mins to clear plant batching queue.`
            : 'Plant batching queue operating within 20m target.'}
        </p>
      </div>
    );
  }

  // Render Transit Lead-Time Buffer Card
  if (model_name === 'delay_regressor') {
    const delayMins = predicted_value ?? prediction_outputs?.predicted_delay_mins ?? 0;
    const bufferMins = prediction_outputs?.recommended_lead_time_buffer_mins ?? (delayMins > 15 ? Math.round(delayMins * 0.5) : 0);
    return (
      <div
        className={`p-3.5 rounded-md border border-blue-300 bg-blue-50/70 text-blue-900 space-y-2 shadow-2xs ${className}`}
        data-testid="transit-buffer-card"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Truck className="w-4 h-4 text-blue-700" />
            <span className="font-bold text-xs uppercase tracking-wider text-blue-900">Transit Delay Forecast</span>
          </div>
          <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md border bg-white border-blue-300 text-blue-800 tabular-nums">
            +{delayMins.toFixed(1)}m Transit Delay
          </span>
        </div>
        <p className="text-xs font-medium text-slate-800">
          {bufferMins > 0
            ? `Recommended Action: Stage mixer truck ${bufferMins} mins earlier to absorb peak road traffic.`
            : 'Transit traffic conditions normal.'}
        </p>
      </div>
    );
  }

  // Render Customer SLA Risk Card
  if (model_name === 'sla_breach_classifier') {
    const probability = predicted_value ?? prediction_outputs?.sla_breach_probability ?? 0;
    const penaltyInr = sla_penalty_risk_inr ?? financial_exposure_inr ?? prediction_outputs?.sla_penalty_risk_inr ?? 0;
    const isHighRisk = probability >= 0.5;
    return (
      <div
        className={`p-3.5 rounded-md border space-y-2 shadow-2xs ${
          isHighRisk
            ? 'border-rose-300 bg-rose-50/70 text-rose-900'
            : 'border-emerald-300 bg-emerald-50/70 text-emerald-900'
        } ${className}`}
        data-testid="sla-risk-card"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className={`w-4 h-4 ${isHighRisk ? 'text-rose-700' : 'text-emerald-700'}`} />
            <span className="font-bold text-xs uppercase tracking-wider">Customer SLA Overrun Risk</span>
          </div>
          <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md border bg-white border-slate-200 text-slate-800 tabular-nums">
            {(probability * 100).toFixed(0)}% Overrun Risk
          </span>
        </div>
        {penaltyInr > 0 && (
          <p className="text-xs font-bold font-mono tabular-nums text-rose-700">
            Estimated SLA Loss Exposure: ₹{penaltyInr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        )}
        <p className="text-xs font-medium text-slate-800">
          {isHighRisk
            ? 'Recommended Action: Advance dispatch priority to prevent site retention penalty.'
            : 'Delivery projected to arrive on time.'}
        </p>
      </div>
    );
  }

  // Render Plant Congestion Indicator
  if (model_name === 'plant_risk_classifier') {
    const rawClass = predicted_value ?? prediction_outputs?.multiclass_class ?? 0;
    const riskLevelMap: Record<number, { label: string; bg: string; border: string; color: string }> = {
      0: { label: 'Optimal Throughput', bg: 'bg-emerald-50', border: 'border-emerald-300', color: 'text-emerald-800' },
      1: { label: 'Moderate Congestion', bg: 'bg-amber-50', border: 'border-amber-300', color: 'text-amber-800' },
      2: { label: 'Severe Bottleneck', bg: 'bg-rose-50', border: 'border-rose-300', color: 'text-rose-800' },
    };
    const riskInfo = riskLevelMap[rawClass] || riskLevelMap[0];
    return (
      <div
        className={`p-3.5 rounded-md border border-slate-200 bg-white text-slate-900 space-y-2 shadow-2xs ${className}`}
        data-testid="plant-risk-card"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-blue-700" />
            <span className="font-bold text-xs uppercase tracking-wider text-slate-900">Plant Capacity &amp; Congestion</span>
          </div>
          <span
            className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-md border ${riskInfo.bg} ${riskInfo.border} ${riskInfo.color}`}
          >
            {riskInfo.label}
          </span>
        </div>
        <p className="text-xs font-medium text-slate-800">
          {rawClass > 0
            ? 'Recommended Action: Balance outgoing concrete orders across adjacent plant silos.'
            : 'Plant batching operating at nominal capacity.'}
        </p>
      </div>
    );
  }

  return null;
};
