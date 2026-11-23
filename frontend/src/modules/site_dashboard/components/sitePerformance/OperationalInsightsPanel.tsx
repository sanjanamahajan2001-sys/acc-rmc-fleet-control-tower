import React from 'react';

export interface InsightItem {
  category: string;
  title: string;
  impact_level: string;
  insight_text: string;
}

interface OperationalInsightsPanelProps {
  insights: InsightItem[];
}

export const OperationalInsightsPanel: React.FC<OperationalInsightsPanelProps> = ({ insights }) => {
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        OPERATIONAL SLA INSIGHTS & PERFORMANCE HEALTH
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {insights.map((item, idx) => (
          <div key={idx} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-indigo-400 font-mono uppercase">{item.category}</span>
              <span className="px-2 py-0.5 rounded text-[9.5px] font-extrabold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                {item.impact_level} Impact
              </span>
            </div>
            <h4 className="text-xs font-extrabold text-slate-100">{item.title}</h4>
            <p className="text-xs text-slate-400 leading-relaxed">{item.insight_text}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
