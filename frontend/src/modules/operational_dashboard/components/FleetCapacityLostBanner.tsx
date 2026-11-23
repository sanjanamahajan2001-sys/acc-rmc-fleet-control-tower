import React from 'react';
import { IconTransitMixer } from '../../../components/icons/LinealColorIcons';

export const FleetCapacityLostBanner: React.FC = () => {
  return (
    <div
      className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between items-center text-center transition-colors min-h-[280px]"
    >
      <div className="w-full space-y-3">
        {/* Title */}
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
          Fleet Capacity Lost
        </h3>

        {/* Clean Frameless Floating Icon - Option A */}
        <div className="flex justify-center py-2">
          <IconTransitMixer className="w-10 h-10 object-contain drop-shadow-sm" />
        </div>

        {/* Primary Metric */}
        <div>
          <span className="text-3xl font-bold font-mono tabular-nums text-slate-900">3.3</span>
          <p className="text-xs font-medium text-slate-500 mt-0.5">Transit Mixers Lost</p>
        </div>
      </div>

      {/* Footer Metric */}
      <div className="w-full pt-3 border-t border-slate-100 space-y-0.5">
        <p className="text-[11px] uppercase font-semibold text-slate-500">Potential Revenue Lost</p>
        <p className="text-sm font-bold font-mono tabular-nums text-rose-700">₹24,750</p>
        <p className="text-[10px] font-mono text-slate-400">Yesterday</p>
      </div>
    </div>
  );
};
