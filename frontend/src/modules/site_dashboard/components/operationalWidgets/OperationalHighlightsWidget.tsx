import React from 'react';

export interface OperationalHighlightItem {
  highlight_key: string;
  title: string;
  metric_value: string;
  status: 'OPTIMAL' | 'ATTENTION' | 'CRITICAL' | 'INFO';
}

interface OperationalHighlightsWidgetProps {
  highlights: OperationalHighlightItem[];
}

export const OperationalHighlightsWidget: React.FC<OperationalHighlightsWidgetProps> = ({ highlights }) => {
  if (!highlights || highlights.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 italic border border-slate-800/80 rounded-xl bg-slate-950/60">
        No operational highlights available for active filters.
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    OPTIMAL: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    ATTENTION: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    CRITICAL: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    INFO: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        AUTOMATED OPERATIONAL HIGHLIGHTS & SUMMARY OBSERVATIONS
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {highlights.map((h) => (
          <div key={h.highlight_key} className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block truncate">{h.title}</span>
            <p className={`text-sm font-black font-mono truncate px-1.5 py-0.5 rounded border ${statusColors[h.status]}`}>
              {h.metric_value || 'No significant issue detected'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
