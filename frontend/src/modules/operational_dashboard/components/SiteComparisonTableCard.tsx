import React from 'react';
import { useSiteComparison } from '../hooks/useSiteComparison';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';

export const SiteComparisonTableCard: React.FC = () => {
  const { data, loading, error, status } = useSiteComparison();

  const isNoObs = status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || !data?.data || data.data.length === 0;
  const sites = data?.data || [];

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 shadow-xl flex flex-col justify-between h-full min-h-[340px] transition-all duration-200 hover:border-slate-700/80">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 tracking-tight flex items-center gap-2">
              <span>SITE COMPARISON &amp; BENCHMARKING</span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Plant operational benchmarking across volume, holding, retention, queue &amp; SLA accuracy
            </p>
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wide uppercase text-sky-400 bg-sky-500/10 border border-sky-500/20">
            WS-04
          </span>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-2">
            <div className="w-6 h-6 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-400 font-mono">Loading site comparison metrics...</span>
          </div>
        ) : error ? (
          <div className="py-10 text-center space-y-2">
            <div className="text-xs text-rose-400 font-medium">Failed to load site comparison</div>
            <div className="text-[11px] text-slate-500 max-w-xs mx-auto">{error}</div>
          </div>
        ) : isNoObs ? (
          <div className="py-12 text-center space-y-2">
            <div className="text-xs font-semibold text-slate-400">NO OBSERVATIONS</div>
            <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
              No site comparison observations available for active filters.
            </p>
          </div>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/40 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800/80">
                <tr>
                  <th scope="col" className="pb-2 pl-1 font-mono w-8 text-center">#</th>
                  <th scope="col" className="pb-2">SITE NAME</th>
                  <th scope="col" className="pb-2 text-right">DISPATCHES</th>
                  <th scope="col" className="pb-2 text-right">VOL (CUM)</th>
                  <th scope="col" className="pb-2 text-right">HOLD (M)</th>
                  <th scope="col" className="pb-2 text-right">RET (M)</th>
                  <th scope="col" className="pb-2 text-right">QUEUE</th>
                  <th scope="col" className="pb-2 text-right">DAS %</th>
                  <th scope="col" className="pb-2 text-center">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 font-mono">
                {sites.map((s) => (
                  <tr key={s.site_code} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 pl-1 text-center font-bold text-slate-400 text-[11px]">
                      {s.rank}
                    </td>
                    <td className="py-2.5 font-sans font-medium text-slate-200 truncate max-w-[140px]" title={s.site_name}>
                      {s.site_name}
                    </td>
                    <td className="py-2.5 text-right font-bold text-slate-100">
                      {s.dispatches}
                    </td>
                    <td className="py-2.5 text-right text-slate-300">
                      {s.volume_cum.toFixed(1)}
                    </td>
                    <td className="py-2.5 text-right text-slate-300">
                      {s.avg_holding_mins.toFixed(1)}
                    </td>
                    <td className="py-2.5 text-right text-slate-300">
                      {s.avg_retention_mins.toFixed(1)}
                    </td>
                    <td className="py-2.5 text-right font-bold text-amber-400">
                      {s.max_queue_tms}
                    </td>
                    <td className="py-2.5 text-right font-bold text-slate-100">
                      {s.dispatch_accuracy.toFixed(1)}%
                    </td>
                    <td className="py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        s.status === 'Optimal' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                        s.status === 'Good' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        s.status === 'Warning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer / Caption */}
      <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-medium text-slate-400">
        <span>Showing {sites.length} Active Sites</span>
        <span className="font-mono text-slate-400">WS-04 PHASE 3F</span>
      </div>
    </div>
  );
};
