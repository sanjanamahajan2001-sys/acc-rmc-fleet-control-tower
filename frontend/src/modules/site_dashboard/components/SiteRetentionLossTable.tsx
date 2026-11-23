import React, { useState, useMemo } from 'react';
import {
  IconPlantRetentionFactory,
  IconSearchGlass,
  IconCriticalAlert,
} from '../../../components/icons/LinealColorIcons';

export interface SiteRetentionLossRowDTO {
  rank: number;
  customer_id: string;
  customer_code: string;
  customer_name: string;
  affected_trips: number;
  avg_excess_retention_mins: number;
  total_excess_retention_mins: number;
  total_excess_retention_formatted: string;
}

export interface SiteRetentionLossTableProps {
  data: SiteRetentionLossRowDTO[];
  totalAffectedClients: number;
  loading?: boolean;
}

export const SiteRetentionLossTable: React.FC<SiteRetentionLossTableProps> = ({
  data,
  totalAffectedClients,
  loading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  // Live client search filtering & page reset on search change
  const filteredData = useMemo(() => {
    setCurrentPage(1);
    if (!searchTerm.trim()) return data;
    const query = searchTerm.toLowerCase();
    return data.filter(
      (row) =>
        row.customer_name.toLowerCase().includes(query) ||
        row.customer_code.toLowerCase().includes(query)
    );
  }, [data, searchTerm]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize));
  const paginatedData = useMemo(() => {
    const startIdx = (currentPage - 1) * pageSize;
    return filteredData.slice(startIdx, startIdx + pageSize);
  }, [filteredData, currentPage, pageSize]);

  // Determine max avg excess for scaling the progress bar width
  const maxAvgExcess = useMemo(() => {
    if (!data || data.length === 0) return 100;
    const maxVal = Math.max(...data.map((d) => d.avg_excess_retention_mins));
    return Math.max(maxVal, 30);
  }, [data]);

  return (
    <div className="rounded-lg p-4 shadow-2xs border border-slate-200/90 bg-white transition-all flex flex-col justify-between">
      <div>
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <IconPlantRetentionFactory className="w-5 h-5 shrink-0" />
              <h3 className="text-sm font-bold tracking-tight text-slate-800">
                Site Retention (&gt;10 mins.)
              </h3>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-rose-50 text-rose-800 border border-rose-200/70">
                {totalAffectedClients} affected clients
              </span>
            </div>
          </div>

          {/* Client Search Bar & Sorting Label */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <IconSearchGlass className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search client..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-2.5 py-1 text-xs rounded-md border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-700 transition-colors w-40 sm:w-48 text-slate-800"
              />
            </div>
          </div>
        </div>

        {/* Table Container */}
        <div className="mt-3 overflow-x-auto min-h-[360px]">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-2">
              <div className="w-7 h-7 rounded-full border-2 border-rose-600 border-t-transparent animate-spin" />
              <span className="text-xs font-medium text-slate-500">Loading retention loss breakdown...</span>
            </div>
          ) : filteredData.length === 0 ? (
            <div className="py-14 text-center space-y-2">
              <IconCriticalAlert className="w-6 h-6 mx-auto" />
              <p className="text-xs font-medium text-slate-500">
                {searchTerm ? `No clients found matching "${searchTerm}"` : 'No clients recorded with retention time beyond 10 minutes.'}
              </p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-[10px] font-bold uppercase tracking-wider text-slate-600 bg-slate-50">
                  <th className="py-2 px-2.5 w-12">RANK</th>
                  <th className="py-2 px-2.5">CLIENT</th>
                  <th className="py-2 px-2.5 w-48 text-center">AVG EXCESS RETENTION</th>
                  <th className="py-2 px-2.5 text-right">TOTAL EXCESS</th>
                  <th className="py-2 px-2.5 text-center">TRIPS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedData.map((row) => {
                  const barWidthPct = Math.min(100, Math.max(10, (row.avg_excess_retention_mins / maxAvgExcess) * 100));

                  return (
                    <tr key={row.customer_id} className="hover:bg-slate-50/80 transition-colors">
                      {/* Rank Badge */}
                      <td className="py-2 px-2.5 font-semibold text-slate-500">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-md font-bold text-[10.5px] bg-slate-100 text-slate-700 font-mono">
                          {row.rank}
                        </span>
                      </td>

                      {/* Client Name */}
                      <td className="py-2 px-2.5 font-semibold tracking-tight text-slate-900 truncate max-w-[130px]" title={row.customer_name}>
                        {row.customer_name}
                      </td>

                      {/* Progress Bar + Value */}
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-2 justify-center">
                          <div className="w-24 h-2 rounded-full overflow-hidden bg-slate-100">
                            <div
                              className="h-full rounded-full transition-all duration-300 bg-rose-500"
                              style={{ width: `${barWidthPct}%` }}
                            />
                          </div>
                          <span className="font-mono tabular-nums text-xs font-semibold w-14 text-left text-slate-800">
                            {row.avg_excess_retention_mins.toFixed(1)}m
                          </span>
                        </div>
                      </td>

                      {/* Total Excess Retention (HH:MM) */}
                      <td className="py-2 px-2.5 text-right font-mono tabular-nums font-semibold text-xs text-slate-900">
                        {row.total_excess_retention_formatted}
                      </td>

                      {/* Affected Trips Tag */}
                      <td className="py-2 px-2.5 text-center">
                        <span className="inline-block px-2 py-0.5 rounded-md font-mono tabular-nums text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                          {row.affected_trips}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Pagination Footer */}
      {!loading && filteredData.length > 0 && (
        <div className="pt-2.5 mt-2 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <span className="font-medium text-slate-500">
            Showing <span className="font-semibold text-slate-800 font-mono">{(currentPage - 1) * pageSize + 1}</span> to{' '}
            <span className="font-semibold text-slate-800 font-mono">{Math.min(currentPage * pageSize, filteredData.length)}</span> of{' '}
            <span className="font-semibold text-slate-800 font-mono">{filteredData.length}</span> clients
          </span>

          <div className="flex items-center space-x-1 self-end sm:self-auto">
            <button
              type="button"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              className="px-2.5 py-1 rounded-md text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
            >
              Prev
            </button>

            <span className="px-2.5 py-1 font-mono font-semibold text-xs text-slate-800">
              {currentPage}/{totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              className="px-2.5 py-1 rounded-md text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
