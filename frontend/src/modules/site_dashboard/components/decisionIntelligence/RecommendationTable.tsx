import React from 'react';

export interface RecommendationRow {
  recommendation_id: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  recommendation_text: string;
  underlying_reason: string;
  affected_plant: string;
  affected_vehicle: string;
  expected_impact: string;
  confidence_pct: number;
  status: 'Pending' | 'Applied' | 'Dismissed';
}

interface RecommendationTableProps {
  recommendations: RecommendationRow[];
}

export const RecommendationTable: React.FC<RecommendationTableProps> = ({ recommendations }) => {
  const priorityStyles: Record<string, string> = {
    CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    HIGH: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    LOW: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        RECOMMENDED OPERATIONAL ACTIONS & PRIORITIZED DECISIONS
      </h3>

      {recommendations.length === 0 ? (
        <div className="p-6 text-center text-xs text-slate-500 italic border border-slate-800/80 rounded-xl bg-slate-950/60">
          No operational recommendations required at this time. All dispatches operating within SLA thresholds.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl bg-slate-950/80 border border-slate-800/90">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
              <tr>
                <th className="px-3.5 py-2.5">Priority</th>
                <th className="px-3.5 py-2.5">Recommendation</th>
                <th className="px-3.5 py-2.5">Reason</th>
                <th className="px-3.5 py-2.5">Affected Plant</th>
                <th className="px-3.5 py-2.5">Vehicle</th>
                <th className="px-3.5 py-2.5 text-right">Expected Impact</th>
                <th className="px-3.5 py-2.5 text-right">Confidence</th>
                <th className="px-3.5 py-2.5 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {recommendations.map((r) => (
                <tr key={r.recommendation_id} className="hover:bg-slate-900/60 transition">
                  <td className="px-3.5 py-2">
                    <span className={`px-2 py-[2px] rounded text-[9.5px] font-extrabold uppercase border ${priorityStyles[r.priority]}`}>
                      {r.priority}
                    </span>
                  </td>
                  <td className="px-3.5 py-2 text-slate-100 font-semibold">{r.recommendation_text}</td>
                  <td className="px-3.5 py-2 text-slate-400 text-[11px]">{r.underlying_reason}</td>
                  <td className="px-3.5 py-2 text-slate-300">{r.affected_plant}</td>
                  <td className="px-3.5 py-2 font-mono text-indigo-400 font-bold">{r.affected_vehicle}</td>
                  <td className="px-3.5 py-2 font-mono text-emerald-400 font-bold text-right">{r.expected_impact}</td>
                  <td className="px-3.5 py-2 font-mono text-indigo-300 text-right">{r.confidence_pct}%</td>
                  <td className="px-3.5 py-2 text-center">
                    <span className="px-2 py-[2px] rounded text-[9.5px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
