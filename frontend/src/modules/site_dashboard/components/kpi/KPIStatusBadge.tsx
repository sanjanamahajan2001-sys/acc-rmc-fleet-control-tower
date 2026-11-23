import React from 'react';

interface KPIStatusBadgeProps {
  status: 'OPTIMAL' | 'WARNING' | 'CRITICAL';
}

export const KPIStatusBadge: React.FC<KPIStatusBadgeProps> = ({ status }) => {
  const styles = {
    OPTIMAL: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    WARNING: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    CRITICAL: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  }[status] || 'bg-slate-800 text-slate-400 border-slate-700';

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border tracking-wider uppercase ${styles}`}>
      {status}
    </span>
  );
};
