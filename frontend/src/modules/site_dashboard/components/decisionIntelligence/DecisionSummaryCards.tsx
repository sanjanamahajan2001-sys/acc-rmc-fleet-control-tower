import React from 'react';

export interface DecisionSummary {
  active_recommendations: number;
  high_priority_issues: number;
  estimated_delay_reduction_mins: number;
  estimated_sla_recovery_pct: number;
  fleet_efficiency_opportunity_pct: number;
}

interface DecisionSummaryCardsProps {
  summary: DecisionSummary;
}

export const DecisionSummaryCards: React.FC<DecisionSummaryCardsProps> = ({ summary }) => {
  const cards = [
    { label: 'Active Recommendations', value: summary.active_recommendations, color: 'text-indigo-400' },
    { label: 'SLA Breach Events', value: summary.high_priority_issues, color: 'text-rose-400' },
    { label: 'Est. Recoverable Delay', value: summary.estimated_delay_reduction_mins + ' min', color: 'text-emerald-400' },
    { label: 'Est. SLA Recovery', value: summary.estimated_sla_recovery_pct + '%', color: 'text-emerald-400' },
    { label: 'Fleet Efficiency Opp.', value: summary.fleet_efficiency_opportunity_pct + '%', color: 'text-amber-400' },
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
