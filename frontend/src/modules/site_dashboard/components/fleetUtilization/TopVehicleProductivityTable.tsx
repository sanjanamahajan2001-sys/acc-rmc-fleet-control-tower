import React from 'react';

export interface VehicleProductivityItem {
  vehicle_plate: string;
  dispatch_count: number;
  total_volume_m3: number;
  avg_holding_mins: number;
  avg_unloading_mins: number;
  avg_retention_mins: number;
  utilization_pct: number;
  status: string;
}

interface TopVehicleProductivityTableProps {
  vehicles: VehicleProductivityItem[];
}

export const TopVehicleProductivityTable: React.FC<TopVehicleProductivityTableProps> = ({ vehicles }) => {
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        TOP 10 VEHICLES BY DISPATCH PRODUCTIVITY & LIFECYCLE
      </h3>

      <div className="overflow-x-auto rounded-xl bg-slate-950/80 border border-slate-800/90">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
            <tr>
              <th className="px-3.5 py-2.5">Vehicle</th>
              <th className="px-3.5 py-2.5 text-right">Dispatches</th>
              <th className="px-3.5 py-2.5 text-right">
                <span className="inline-flex items-center justify-end gap-1 cursor-help group" title="Estimated based on rated 7.5 m³ TM drum capacity">
                  Est. Volume (m³)
                  <span className="w-3.5 h-3.5 rounded-full bg-slate-800 text-slate-400 group-hover:bg-indigo-600 group-hover:text-white inline-flex items-center justify-center text-[9px] font-bold transition">
                    i
                  </span>
                </span>
              </th>
              <th className="px-3.5 py-2.5 text-right">Avg Holding</th>
              <th className="px-3.5 py-2.5 text-right">Avg Unload</th>
              <th className="px-3.5 py-2.5 text-right">Avg Retention</th>
              <th className="px-3.5 py-2.5 text-right">Utilization</th>
              <th className="px-3.5 py-2.5 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-medium">
            {vehicles.map((v) => (
              <tr key={v.vehicle_plate} className="hover:bg-slate-900/60 transition">
                <td className="px-3.5 py-2 font-mono text-indigo-400 font-bold">{v.vehicle_plate}</td>
                <td className="px-3.5 py-2 font-mono text-slate-200 font-bold text-right">{v.dispatch_count}</td>
                <td className="px-3.5 py-2 font-mono text-slate-300 text-right">{v.total_volume_m3}</td>
                <td className="px-3.5 py-2 font-mono text-rose-400 font-bold text-right">{v.avg_holding_mins}m</td>
                <td className="px-3.5 py-2 font-mono text-indigo-400 font-bold text-right">{v.avg_unloading_mins}m</td>
                <td className="px-3.5 py-2 font-mono text-amber-400 font-bold text-right">{v.avg_retention_mins}m</td>
                <td className="px-3.5 py-2 font-mono text-emerald-400 font-bold text-right">{v.utilization_pct}%</td>
                <td className="px-3.5 py-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-[9.5px] font-extrabold uppercase border ${
                    v.status === 'OPTIMAL' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                  }`}>
                    {v.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
