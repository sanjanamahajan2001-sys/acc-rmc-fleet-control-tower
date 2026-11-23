import React from 'react';

interface TMDetailsStatusBadgeProps {
  status: 'OPTIMAL' | 'WARNING' | 'CRITICAL' | 'DELAYED' | string;
}

export const TMDetailsStatusBadge: React.FC<TMDetailsStatusBadgeProps> = ({ status }) => {
  const styles: Record<string, string> = {
    OPTIMAL: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    WARNING: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    DELAYED: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    COMPLETED: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  };

  const badgeStyle = styles[status] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`px-2 py-[2px] rounded text-[9.5px] font-extrabold uppercase border tracking-wider ${badgeStyle}`}>
      {status}
    </span>
  );
};
