import React from 'react';

export interface VehicleAlert {
  vehicle_plate: string;
  alert_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  message: string;
}

interface FleetHealthPanelProps {
  alerts: VehicleAlert[];
}

export const FleetHealthPanel: React.FC<FleetHealthPanelProps> = ({ alerts }) => {
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        OPERATIONAL VEHICLE ALERTS & BOTTLENECK WARNINGS
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {alerts.map((a, idx) => (
          <div key={idx} className="p-3 rounded-xl bg-slate-950/90 border border-slate-800/90 space-y-1">
            <div className="flex items-center justify-between pb-1 border-b border-slate-800/60">
              <span className="font-mono text-sm font-black text-indigo-300 tracking-wider">{a.vehicle_plate}</span>
              <span className={`px-2 py-[2px] rounded text-[9px] font-extrabold uppercase border ${
                a.severity === 'HIGH' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
              }`}>
                {a.severity} SEVERITY
              </span>
            </div>
            <h4 className="text-xs font-bold text-slate-200">{a.alert_type}</h4>
            <p className="text-xs text-slate-400 leading-relaxed">{a.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
