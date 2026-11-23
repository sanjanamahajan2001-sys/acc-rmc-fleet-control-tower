import React, { useState, useMemo, useEffect } from 'react';
import { SiteReadinessDTO, OperationalGradeEnum } from '../hooks/useSiteReadiness';
import { X, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface SiteReadinessDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sites: SiteReadinessDTO[];
  totalCount: number;
}

export const SiteReadinessDrawer: React.FC<SiteReadinessDrawerProps> = ({
  isOpen,
  onClose,
  sites,
  totalCount,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    setCurrentPage(1);
    setSearchQuery('');
  }, [isOpen]);

  const filteredSites = useMemo(() => {
    if (!searchQuery.trim()) return sites;
    const q = searchQuery.toLowerCase().trim();
    return sites.filter(
      (s) =>
        s.site_name?.toLowerCase().includes(q) ||
        s.site_id?.toLowerCase().includes(q)
    );
  }, [sites, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredSites.length / pageSize));
  const paginatedSites = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredSites.slice(start, start + pageSize);
  }, [filteredSites, currentPage, pageSize]);

  if (!isOpen) return null;

  const getGradeBadge = (grade: OperationalGradeEnum) => {
    switch (grade) {
      case OperationalGradeEnum.GRADE_A:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200">A • Optimal</span>;
      case OperationalGradeEnum.GRADE_B:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200">B • Good</span>;
      case OperationalGradeEnum.GRADE_C:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200">C • Warning</span>;
      case OperationalGradeEnum.GRADE_D:
      default:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-rose-700 bg-rose-50 border border-rose-200">D • Critical</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end transition-opacity duration-300">
      <div className="w-full max-w-4xl bg-white border-l border-slate-200 text-slate-900 flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold tracking-tight text-slate-900">SITE READINESS INDEX DETAILS</h2>
              <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                {totalCount} Sites
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Composite Operational Grade evaluated across SWI, DPI, and FUI
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="Close Drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Toolbar */}
        <div className="px-5 py-3 border-b border-slate-100 bg-white flex items-center justify-between gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search by site or customer name..."
              className="w-full pl-8 pr-7 py-1.5 rounded-md border border-slate-200 bg-white text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <span className="text-[11px] font-mono tabular-nums text-slate-500">
            {searchQuery
              ? `Matches: ${filteredSites.length} of ${sites.length}`
              : `Total Records: ${sites.length}`}
          </span>
        </div>

        {/* Content Table */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {sites.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              No site readiness observations available for this scope.
            </div>
          ) : filteredSites.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm italic">
              No sites match query &quot;{searchQuery}&quot;.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-left text-xs text-slate-800 min-w-[700px]">
                <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[10px]">
                  <tr>
                    <th scope="col" className="px-3 py-2.5 text-center w-12">Rank</th>
                    <th scope="col" className="px-3 py-2.5">Site / Customer</th>
                    <th scope="col" className="px-3 py-2.5 text-right">Trips</th>
                    <th scope="col" className="px-3 py-2.5 text-right">SWI</th>
                    <th scope="col" className="px-3 py-2.5 text-right">DPI</th>
                    <th scope="col" className="px-3 py-2.5 text-right">FUI</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-bold text-slate-900">SRI Score</th>
                    <th scope="col" className="px-3 py-2.5 text-center">Grade</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {paginatedSites.map((s) => (
                    <tr key={s.site_id} className="hover:bg-slate-50/75 transition-colors">
                      <td className="px-3 py-2.5 text-center text-slate-500 font-mono text-[11px]">{s.rank}</td>
                      <td className="px-3 py-2.5 font-medium text-slate-900">{s.site_name}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-600">{s.total_trips.toLocaleString()}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-600">{s.swi_site.toFixed(1)}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-600">{s.dpi_site.toFixed(1)}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-600">{s.fui_site.toFixed(1)}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums font-bold text-slate-900">{s.sri_score.toFixed(1)}</td>
                      <td className="px-3 py-2.5 text-center">{getGradeBadge(s.grade)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* 10-Row Pagination Bar */}
              {totalPages > 1 && (
                <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs text-slate-600">
                  <div>
                    Showing <strong className="text-slate-900 font-mono">{paginatedSites.length}</strong> of{' '}
                    <strong className="text-slate-900 font-mono">{filteredSites.length}</strong> records
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                      title="Previous Page"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <span className="font-mono text-[11px] px-1.5">
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                      className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                      title="Next Page"
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
