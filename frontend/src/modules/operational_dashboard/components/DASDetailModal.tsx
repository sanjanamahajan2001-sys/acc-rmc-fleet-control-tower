import { env } from '../../../config/env';
import React, { useEffect, useState, useMemo } from 'react';
import { DASSummaryDTO, DASBucketBreakdownDTO } from '../hooks/useDASOverview';
import { DASDetailRowDTO } from '../hooks/useDASDetails';
import { X, AlertCircle, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface DASDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary?: DASSummaryDTO | null;
  buckets?: DASBucketBreakdownDTO | null;
  detailRows?: DASDetailRowDTO[];
  hasDetailApi?: boolean;
  isLoading?: boolean;
}

export const DASDetailModal: React.FC<DASDetailModalProps> = ({
  isOpen,
  onClose,
  summary,
  buckets,
  detailRows = [],
  hasDetailApi = true,
  isLoading = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    setCurrentPage(1);
    setSearchQuery('');
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return detailRows;
    const q = searchQuery.toLowerCase().trim();
    return detailRows.filter(
      (row) =>
        row.customer_name?.toLowerCase().includes(q) ||
        row.customer_id?.toLowerCase().includes(q)
    );
  }, [detailRows, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, currentPage, pageSize]);

  if (!isOpen) return null;

  const isNoObs = !summary || summary.total_dispatches === 0 || summary.das_score === null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end transition-opacity duration-300"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-4xl bg-white border-l border-slate-200 text-slate-900 flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold tracking-tight text-slate-900">DISPATCH ACCURACY DETAILS</h2>
              {summary?.operational_status && !isNoObs && (
                <span
                  className={`px-2 py-0.5 rounded-md text-xs font-semibold uppercase tracking-wider ${
                    summary.operational_status === 'OPTIMAL'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : summary.operational_status === 'WARNING'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}
                >
                  {summary.operational_status}
                </span>
              )}
              {detailRows.length > 0 && (
                <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  {detailRows.length} Customers
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Target Arrival &plusmn; 20 min tolerance window &bull; Holding &gt; 20m &bull; Retention &gt; 10m
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="Close Modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Toolbar */}
        {!isNoObs && detailRows.length > 0 && (
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
                placeholder="Search by customer name..."
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
                ? `Matches: ${filteredRows.length} of ${detailRows.length}`
                : `Total Records: ${detailRows.length}`}
            </span>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Section A: KPI Summary & Variance Buckets */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">DAS Score</span>
              <span className="text-lg font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                {summary?.das_score !== null && summary?.das_score !== undefined
                  ? summary.das_score.toFixed(1) + '%'
                  : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-400 mt-0.5">Target: &ge; 70.0%</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Total Dispatches</span>
              <span className="text-lg font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                {summary?.total_dispatches ? summary.total_dispatches.toLocaleString() : '0'}
              </span>
              <span className="text-[10px] text-slate-400 mt-0.5">All Completed Trips</span>
            </div>

            <div className="bg-emerald-50/50 border border-emerald-200 rounded-lg p-3 flex flex-col">
              <span className="text-[10px] text-emerald-700 uppercase tracking-wider font-semibold">Within 20m</span>
              <span className="text-lg font-bold text-emerald-800 font-mono tabular-nums mt-0.5">
                {buckets?.within_20m_pct !== undefined ? buckets.within_20m_pct.toFixed(1) + '%' : '0.0%'}
              </span>
              <span className="text-[10px] text-emerald-600 mt-0.5">({buckets?.within_20m_count ? buckets.within_20m_count.toLocaleString() : 0} trips)</span>
            </div>

            <div className="bg-amber-50/50 border border-amber-200 rounded-lg p-3 flex flex-col">
              <span className="text-[10px] text-amber-700 uppercase tracking-wider font-semibold">20&ndash;40m</span>
              <span className="text-lg font-bold text-amber-800 font-mono tabular-nums mt-0.5">
                {buckets?.moderate_20_40m_pct !== undefined ? buckets.moderate_20_40m_pct.toFixed(1) + '%' : '0.0%'}
              </span>
              <span className="text-[10px] text-amber-600 mt-0.5">({buckets?.moderate_20_40m_count ? buckets.moderate_20_40m_count.toLocaleString() : 0} trips)</span>
            </div>

            <div className="bg-rose-50/50 border border-rose-200 rounded-lg p-3 flex flex-col">
              <span className="text-[10px] text-rose-700 uppercase tracking-wider font-semibold">&gt;40m</span>
              <span className="text-lg font-bold text-rose-800 font-mono tabular-nums mt-0.5">
                {buckets?.critical_above_40m_pct !== undefined ? buckets.critical_above_40m_pct.toFixed(1) + '%' : '0.0%'}
              </span>
              <span className="text-[10px] text-rose-600 mt-0.5">({buckets?.critical_above_40m_count ? buckets.critical_above_40m_count.toLocaleString() : 0} trips)</span>
            </div>
          </div>

          {/* Section B: Detail Breakdown Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2.5 pb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Customer DAS Breakdown
              </h3>
              <span className="text-[11px] font-mono tabular-nums text-slate-500 font-normal">
                {searchQuery
                  ? `Showing filtered results (${filteredRows.length})`
                  : `${detailRows.length} Total Customers`}
              </span>
            </div>

            {isNoObs ? (
              <div className="py-12 text-center text-slate-500 text-sm bg-slate-50 border border-slate-200 rounded-lg">
                No dispatch accuracy observations available for this filter scope.
              </div>
            ) : isLoading ? (
              <div className="py-12 text-center text-slate-500 text-sm bg-slate-50 border border-slate-200 rounded-lg animate-pulse">
                Loading customer DAS breakdown...
              </div>
            ) : !hasDetailApi ? (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-amber-900">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <span>Backend Detail API Contract Required</span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  Summary DAS metrics are rendered above directly from the backend <code className="font-mono text-slate-800 bg-slate-100 px-1 py-0.5 rounded">GET /operational-dashboard/das-overview</code> DTO contract.
                </p>
              </div>
            ) : filteredRows.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-sm bg-slate-50 border border-slate-200 rounded-lg italic">
                No customers match query &quot;{searchQuery}&quot;.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                <table className="w-full text-left text-xs text-slate-800 min-w-[700px]">
                  <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[10px]">
                    <tr>
                      <th scope="col" className="px-3 py-2.5 w-12 text-center">Rank</th>
                      <th scope="col" className="px-3 py-2.5">Customer</th>
                      <th scope="col" className="px-3 py-2.5 text-right">Trips</th>
                      <th scope="col" className="px-3 py-2.5 text-right text-emerald-700">&le;20m</th>
                      <th scope="col" className="px-3 py-2.5 text-right text-amber-700">20&ndash;40m</th>
                      <th scope="col" className="px-3 py-2.5 text-right text-rose-700">&gt;40m</th>
                      <th scope="col" className="px-3 py-2.5 text-right font-bold text-blue-700">DAS Score</th>
                      <th scope="col" className="px-3 py-2.5 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {paginatedRows.map((row) => (
                      <tr key={row.customer_id} className="hover:bg-slate-50/75 transition-colors">
                        <td className="px-3 py-2.5 text-center text-slate-500 font-mono text-[11px]">{row.rank}</td>
                        <td className="px-3 py-2.5 font-medium text-slate-900">{row.customer_name}</td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-600">{row.total_dispatches.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums text-emerald-700">{row.accurate_count.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums text-amber-700">{row.moderate_count.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums text-rose-700">{row.critical_count.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums font-bold text-slate-900">{row.das_score.toFixed(1)}%</td>
                        <td className="px-3 py-2.5 text-center">
                          <span
                            className={
                              'px-1.5 py-0.5 rounded-md text-[11px] font-mono font-semibold uppercase tracking-wider border ' +
                              (row.operational_status === 'OPTIMAL'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : row.operational_status === 'WARNING'
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : 'bg-rose-50 text-rose-700 border-rose-200')
                            }
                          >
                            {row.operational_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* 10-Row Pagination Bar */}
                {totalPages > 1 && (
                  <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs text-slate-600">
                    <div>
                      Showing <strong className="text-slate-900 font-mono">{paginatedRows.length}</strong> of{' '}
                      <strong className="text-slate-900 font-mono">{filteredRows.length}</strong> customers
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

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
          <span className="text-[11px] text-slate-500 font-normal">WS-03.4 Dispatch Accuracy Score (DAS)</span>
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-md bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
