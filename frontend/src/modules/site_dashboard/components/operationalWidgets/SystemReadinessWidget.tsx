import React from 'react';

export interface SystemReadinessItem {
  component: string;
  status: 'GOOD' | 'WARNING' | 'CRITICAL';
  detail_statement: string;
}

interface SystemReadinessWidgetProps {
  readiness: SystemReadinessItem[];
}

export const SystemReadinessWidget: React.FC<SystemReadinessWidgetProps> = ({ readiness }) => {
  if (!readiness || readiness.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 italic border border-slate-800/80 rounded-xl bg-slate-950/60">
        No system readiness status available.
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    GOOD: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    WARNING: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        SYSTEM OPERATIONAL READINESS INDICATORS
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {readiness.map((item) => (
          <div key={item.component} className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold text-slate-200">{item.component}</span>
              <span className={`px-2 py-0.5 rounded text-[9.5px] font-extrabold border ${statusColors[item.status]}`}>
                {item.status}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-normal">{item.detail_statement}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
