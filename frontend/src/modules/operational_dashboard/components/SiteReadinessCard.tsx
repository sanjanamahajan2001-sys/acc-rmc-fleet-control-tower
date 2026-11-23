import React, { useState } from 'react';
import { useSiteReadiness, OperationalGradeEnum } from '../hooks/useSiteReadiness';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { SiteReadinessDrawer } from './SiteReadinessDrawer';
import { IconPlantSiteDashboard } from '../../../components/icons/LinealColorIcons';

export const SiteReadinessCard: React.FC = () => {
  const { data, loading, error } = useSiteReadiness();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const sites = data?.data || [];
  const top10 = sites.slice(0, 10);
  const totalCount = data?.total_sites || sites.length;
  const isNoObs = data?.status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || sites.length === 0;

  const getGradeBadge = (grade: OperationalGradeEnum) => {
    switch (grade) {
      case OperationalGradeEnum.GRADE_A:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200">Optimal</span>;
      case OperationalGradeEnum.GRADE_B:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200">Good</span>;
      case OperationalGradeEnum.GRADE_C:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200">Average</span>;
      case OperationalGradeEnum.GRADE_D:
      default:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-rose-700 bg-rose-50 border border-rose-200">Poor</span>;
    }
  };

  return (
    <>
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <IconPlantSiteDashboard className="w-4 h-4" />
                SITE READINESS INDEX (SRI)
              </h3>
              <p className="text-[11px] font-normal text-slate-500 mt-0.5">Composite Site Readiness Across SWI, DPI, and FUI</p>
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
                No site readiness observations available for this scope.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider font-semibold border-b border-slate-200 text-slate-500 bg-slate-50">
                    <tr>
                      <th scope="col" className="py-2 px-2">Site</th>
                      <th scope="col" className="py-2 px-1 text-center">SRI</th>
                      <th scope="col" className="py-2 px-1 text-center">Grade</th>
                      <th scope="col" className="py-2 px-1 text-right">SWI</th>
                      <th scope="col" className="py-2 px-1 text-right">DPI</th>
                      <th scope="col" className="py-2 px-1 text-right">FUI</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {top10.map((s) => (
                      <tr key={s.site_id} className="hover:bg-slate-50/75 transition-colors">
                        <td className="py-2 px-2 font-medium text-slate-900 truncate max-w-[120px]" title={s.site_name}>
                          {s.site_name}
                        </td>
                        <td className="py-2 px-1 text-center">
                          <div className="flex items-center gap-1.5 justify-center">
                            <span className="font-mono tabular-nums font-bold text-slate-900">{Math.round(s.sri_score)}</span>
                            <div className="w-10 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  s.sri_score >= 80 ? 'bg-emerald-600' : s.sri_score >= 60 ? 'bg-blue-600' : s.sri_score >= 40 ? 'bg-amber-500' : 'bg-rose-600'
                                }`}
                                style={{
                                  width: `${Math.min(s.sri_score, 100)}%`,
                                }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-2 px-1 text-center">
                          {getGradeBadge(s.grade)}
                        </td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums text-slate-600">{Math.round(s.swi_site)}</td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums text-slate-600">{Math.round(s.dpi_site)}</td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums text-slate-600">{Math.round(s.fui_site)}</td>
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
            View all sites &rarr;
          </button>
        </div>
      </div>

      {/* Side Drawer Overlay */}
      <SiteReadinessDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        sites={sites}
        totalCount={totalCount}
      />
    </>
  );
};

