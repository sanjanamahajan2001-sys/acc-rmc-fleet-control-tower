import React from 'react';
import { FleetSummaryCards, FleetSummary } from './FleetSummaryCards';
import { TopVehicleProductivityTable, VehicleProductivityItem } from './TopVehicleProductivityTable';
import { FleetHealthPanel, VehicleAlert } from './FleetHealthPanel';

export interface FleetUtilizationContainerData {
  summary: FleetSummary;
  top_vehicles: VehicleProductivityItem[];
  alerts: VehicleAlert[];
}

interface FleetUtilizationContainerProps {
  data: FleetUtilizationContainerData | null;
  loading?: boolean;
}

export const FleetUtilizationContainer: React.FC<FleetUtilizationContainerProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 animate-pulse space-y-4 shadow-xl">
        <div className="h-4 w-64 bg-slate-800 rounded" />
        <div className="h-36 w-full bg-slate-800/80 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 space-y-6 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h2 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
          FLEET UTILIZATION, VEHICLE PRODUCTIVITY & ASSET INTELLIGENCE
        </h2>
        <span className="text-[11px] font-mono text-slate-500 font-bold uppercase">Workstream 2.8 Active</span>
      </div>

      {/* 1. Fleet Summary Metrics */}
      <FleetSummaryCards summary={data.summary} />

      {/* 2. Top 10 Vehicles Productivity Table */}
      <TopVehicleProductivityTable vehicles={data.top_vehicles || []} />

      {/* 3. Fleet Health & Vehicle Operational Warnings */}
      <FleetHealthPanel alerts={data.alerts || []} />
    </div>
  );
};
