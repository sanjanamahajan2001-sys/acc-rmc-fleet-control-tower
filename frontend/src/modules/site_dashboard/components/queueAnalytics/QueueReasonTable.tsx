import React from 'react';

export interface CauseItem {
  rule_code: string;
  potential_reason: string;
  impact_level: string;
  issue_type: string;
  confidence_score: number;
  evidence_statement: string;
}

interface QueueReasonTableProps {
  causes: CauseItem[];
}

export const QueueReasonTable: React.FC<QueueReasonTableProps> = ({ causes }) => {
  const getImpactColor = (impact: string) => {
    if (impact === 'High') return 'text-amber-600 font-bold';
    if (impact === 'Medium') return 'text-amber-500 font-medium';
    return 'text-emerald-600 font-medium';
  };

  const getTypeColor = (type: string) => {
    if (type.includes('Issue') || type.includes('Dispatch')) return 'text-rose-600 font-bold';
    if (type.includes('Mixed')) return 'text-blue-600 font-medium';
    return 'text-slate-600 font-medium';
  };

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3">
      {/* Widget Header matching client reference */}
      <h2 className="text-xs font-bold uppercase tracking-tight text-slate-800">
        WHY DID QUEUE BUILD UP?
      </h2>

      {causes.length === 0 ? (
        <div className="p-6 text-center text-xs italic border border-slate-200 rounded-lg bg-slate-50 text-slate-500">
          No queue build-up reasons detected for active filters.
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-200/90 rounded-md bg-white">
          <table className="w-full text-left text-xs">
            <thead className="text-[10px] uppercase font-bold border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left font-bold text-slate-700">Potential Reason</th>
                <th className="px-3 py-2 text-center font-bold text-slate-700">Impact</th>
                <th className="px-3 py-2 text-left font-bold text-slate-700">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {causes.map((c, idx) => (
                <tr key={`${c.rule_code}-${idx}`} className="transition border-b border-slate-100 text-xs hover:bg-slate-50">
                  <td className="px-3 py-2 font-medium text-slate-900">{c.potential_reason}</td>
                  <td className={`px-3 py-2 text-center ${getImpactColor(c.impact_level)}`}>{c.impact_level}</td>
                  <td className={`px-3 py-2 text-left ${getTypeColor(c.issue_type)}`}>{c.issue_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

