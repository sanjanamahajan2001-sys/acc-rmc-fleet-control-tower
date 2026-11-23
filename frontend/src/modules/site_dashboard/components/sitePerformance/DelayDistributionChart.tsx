import React from 'react';

export interface DelayCategory {
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  count: number;
  percentage: number;
}

interface DelayDistributionChartProps {
  delays: DelayCategory[];
}

export const DelayDistributionChart: React.FC<DelayDistributionChartProps> = ({ delays }) => {
  const colorMap: Record<string, string> = {
    Low: 'bg-emerald-500',
    Medium: 'bg-indigo-500',
    High: 'bg-amber-500',
    Critical: 'bg-rose-500',
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        OPERATIONAL DELAY SEVERITY DISTRIBUTION
      </h3>

      <div className="space-y-2.5 p-4 rounded-xl bg-slate-950/80 border border-slate-800/90">
        {delays.map((d) => (
          <div key={d.severity} className="space-y-1">
            <div className="flex justify-between text-xs font-semibold">
              <span className="text-slate-100 font-mono font-extrabold tracking-wide">{d.severity} Severity Delay</span>
              <span className="text-slate-300 font-bold font-mono">
                {d.count} Dispatches ({d.percentage}%)
              </span>
            </div>
            <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className={`h-full rounded-full transition-all duration-300 ${colorMap[d.severity]}`}
                style={{ width: `${d.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
