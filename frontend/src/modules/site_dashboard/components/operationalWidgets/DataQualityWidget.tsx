import React from 'react';

export interface DataQualityItem {
  issue_category: string;
  issue_count: number;
  status: 'PASS' | 'ATTENTION' | 'FAILED';
  impact_description: string;
  suggested_action: string;
}

interface DataQualityWidgetProps {
  dataQuality: DataQualityItem[];
}

export const DataQualityWidget: React.FC<DataQualityWidgetProps> = ({ dataQuality }) => {
  if (!dataQuality || dataQuality.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-500 italic border border-slate-800/80 rounded-xl bg-slate-950/60">
        No data quality issues detected.
      </div>
    );
  }

  const statusStyles: Record<string, string> = {
    PASS: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    ATTENTION: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    FAILED: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        DATA QUALITY INTELLIGENCE & ERP INTEGRITY METRICS
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {dataQuality.map((dq) => (
          <div key={dq.issue_category} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold text-slate-200">{dq.issue_category}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-black text-slate-100">{dq.issue_count} issues</span>
                <span className={`px-2 py-0.5 rounded text-[9.5px] font-extrabold border ${statusStyles[dq.status]}`}>
                  {dq.status}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{dq.impact_description}</p>
            <div className="pt-1 border-t border-slate-800/60 flex items-center gap-1.5 text-[11px]">
              <span className="text-slate-500 font-bold">Action:</span>
              <span className="text-indigo-300 font-medium">{dq.suggested_action}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
