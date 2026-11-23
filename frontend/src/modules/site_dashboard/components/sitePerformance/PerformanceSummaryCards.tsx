import React from 'react';

export interface PerformanceSummary {
  total_dispatches: number;
  within_sla_count: number;
  outside_sla_count: number;
  compliance_pct: number;
  violation_pct: number;
  avg_holding_mins: number;
  percentile_95_holding_mins: number;
  max_holding_mins: number;
  avg_retention_mins: number;
  max_retention_mins: number;
  avg_site_time_mins: number;
}

interface PerformanceSummaryCardsProps {
  summary: PerformanceSummary;
}

export const PerformanceSummaryCards: React.FC<PerformanceSummaryCardsProps> = ({ summary }) => {
  const cards = [
    { label: 'SLA Compliance Rate', value: summary.compliance_pct + '%', color: 'text-emerald-400' },
    { label: 'SLA Violation Rate', value: summary.violation_pct + '%', color: 'text-rose-400' },
    { label: '95th Percentile Holding', value: summary.percentile_95_holding_mins + ' min', color: 'text-indigo-400' },
    { label: 'Average Site Visit', value: summary.avg_site_time_mins + ' min', color: 'text-slate-100' },
    { label: 'Maximum Site Retention', value: summary.max_retention_mins + ' min', color: 'text-amber-400' },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">{c.label}</span>
          <span className={`text-lg font-black font-mono ${c.color}`}>{c.value}</span>
        </div>
      ))}
    </div>
  );
};
