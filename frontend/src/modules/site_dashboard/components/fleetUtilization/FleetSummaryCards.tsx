import React from 'react';

export interface FleetSummary {
  total_active_vehicles: number;
  vehicles_with_dispatches: number;
  idle_vehicles: number;
  fleet_utilization_pct: number;
  avg_dispatches_per_vehicle: number;
  avg_cycle_time_mins: number;
}

interface FleetSummaryCardsProps {
  summary: FleetSummary;
}

export const FleetSummaryCards: React.FC<FleetSummaryCardsProps> = ({ summary }) => {
  const cards = [
    { label: 'Active Fleet Count', value: summary.total_active_vehicles, color: 'text-slate-100' },
    { label: 'Dispatched TMs', value: summary.vehicles_with_dispatches, color: 'text-indigo-400' },
    { label: 'Idle TMs', value: summary.idle_vehicles, color: 'text-amber-400' },
    { label: 'Fleet Utilization %', value: summary.fleet_utilization_pct + '%', color: 'text-emerald-400' },
    { label: 'Avg Trips / Vehicle', value: summary.avg_dispatches_per_vehicle, color: 'text-indigo-300' },
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
