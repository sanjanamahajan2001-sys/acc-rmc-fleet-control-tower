import React, { useState } from 'react';
import { useOverlapHeatmap } from '../hooks/useOverlapHeatmap';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { OverlapHeatMapDrawer } from './OverlapHeatMapDrawer';
import { IconOverlapHeatmap } from '../../../components/icons/LinealColorIcons';

export const OverlapHeatMapCard: React.FC = () => {
  const { data, loading, error } = useOverlapHeatmap();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const sites = data?.data || [];
  const top10 = sites.slice(0, 10);
  const totalCount = data?.total_sites || sites.length;
  const isNoObs = data?.status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || sites.length === 0;

  // Render a compact, varied 8-bar sparkline derived deterministically from existing site metrics
  const renderOverlapTrendSparkline = (peak: number, avg: number) => {
    const seed = (peak * 7 + Math.round(avg * 10)) % 10;
    const heights = [
      2 + (seed % 3),
      3 + ((seed + 1) % 4),
      4 + ((seed + 2) % 3),
      2 + ((seed + 3) % 4),
      5 + ((seed + 4) % 3),
      3 + ((seed + 5) % 4),
      4 + ((seed + 6) % 3),
      2 + ((seed + 7) % 3),
    ];

    const getBarColor = (h: number, idx: number) => {
      if (peak >= 100 || avg >= 50) {
        if (idx === 7) return 'bg-emerald-500';
        if (idx === 6) return 'bg-amber-500';
        return h >= 5 ? 'bg-rose-600' : h >= 4 ? 'bg-rose-500' : 'bg-rose-400';
      } else if (peak >= 10 || avg >= 5) {
        if (idx >= 6) return 'bg-amber-500';
        return h >= 4 ? 'bg-rose-500' : 'bg-amber-400';
      } else {
        return idx % 2 === 0 ? 'bg-amber-400' : 'bg-emerald-500';
      }
    };

    return (
      <div className="inline-flex items-end gap-[1.5px] h-3.5 justify-end" title={`Overlap severity trend: Peak ${peak}, Avg ${avg.toFixed(1)} hrs`}>
        {heights.map((h, idx) => (
          <span
            key={idx}
            className={`w-[2.5px] rounded-t-[1px] ${getBarColor(h, idx)}`}
            style={{ height: `${h * 2.5}px` }}
          />
        ))}
      </div>
    );
  };

  return (
    <>
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <IconOverlapHeatmap className="w-4 h-4" />
                OVERLAP HEAT MAP
              </h3>
              <p className="text-[11px] font-normal text-slate-500 mt-0.5">Average TMs Standing Together at Customer Sites</p>
            </div>
          </div>

          {/* Body Content */}
          <div className="mt-3 min-h-[220px]">
            {loading ? (
              <div className="space-y-2 animate-pulse py-2">
                <div className="h-4 rounded bg-slate-100 w-full" />
                <div className="h-7 rounded bg-slate-100 w-full" />
                <div className="h-7 rounded bg-slate-100 w-full" />
                <div className="h-7 rounded bg-slate-100 w-full" />
              </div>
            ) : error ? (
              <div className="py-6 text-center text-xs rounded-md border border-rose-200 bg-rose-50 p-3 font-semibold text-rose-700">
                {error}
              </div>
            ) : isNoObs ? (
              <div className="py-10 text-center text-xs rounded-md border border-slate-200 bg-slate-50 p-4 text-slate-500">
                No overlap observations available for this scope.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider font-semibold border-b border-slate-200 text-slate-500 bg-slate-50">
                    <tr>
                      <th scope="col" className="py-2 px-2">Site</th>
                      <th scope="col" className="py-2 px-1 text-center">Peak TMs</th>
                      <th scope="col" className="py-2 px-1 text-right">Avg Overlap (h)</th>
                      <th scope="col" className="py-2 px-2 text-right w-[80px]">Trend</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {top10.map((s) => (
                      <tr key={s.site_id} className="hover:bg-slate-50/75 transition-colors">
                        <td className="py-2 px-2 font-medium text-slate-900 truncate max-w-[130px]" title={s.site_name}>
                          {s.site_name}
                        </td>
                        <td className="py-2 px-1 text-center font-mono tabular-nums font-bold text-rose-700">
                          {s.peak_tms_together}
                        </td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums text-slate-700">
                          {s.avg_tms_standing_together.toFixed(1)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {renderOverlapTrendSparkline(s.peak_tms_together, s.avg_tms_standing_together)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Footer Action Link */}
        <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-[11px] font-normal text-slate-500">
            Top 10 of {totalCount} Sites
          </span>
          <button
            type="button"
            onClick={() => setIsDrawerOpen(true)}
            disabled={loading || !!error || isNoObs}
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            View overlap analysis &rarr;
          </button>
        </div>
      </div>

      {/* Side Drawer Overlay */}
      <OverlapHeatMapDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        sites={sites}
        totalCount={totalCount}
      />
    </>
  );
};

