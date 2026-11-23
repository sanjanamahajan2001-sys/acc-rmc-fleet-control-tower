import React, { useState, useMemo, useEffect } from 'react';
import { ArrowRight, X, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { TMTimelineItem, TimelineData } from '../timeline/types';

interface DispatchIntervalWidgetProps {
  timelineData: TimelineData | null;
  loading?: boolean;
}

interface CalculatedIntervalItem {
  from_to: string;
  dispatch_interval_mins: number;
  unloading_interval_mins: number;
  recommended_interval_mins: number;
  variance_mins: number;
  remarks: string;
}

export const DispatchIntervalWidget: React.FC<DispatchIntervalWidgetProps> = ({ timelineData, loading }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    setCurrentPage(1);
    setSearchQuery('');
  }, [drawerOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerOpen) {
        setDrawerOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [drawerOpen]);

  if (loading || !timelineData || !timelineData.tm_timelines) {
    return (
      <div className="bg-white rounded-lg border border-slate-200/90 p-4 shadow-sm animate-pulse space-y-3">
        <div className="h-4 w-48 bg-slate-200 rounded" />
        <div className="h-44 w-full bg-slate-100 rounded-lg" />
      </div>
    );
  }

  // Parse standard HH:MM time strings into minutes from midnight
  const parseMins = (timeStr?: string): number => {
    if (!timeStr) return 0;
    const clean = timeStr.trim();
    const isPM = clean.toUpperCase().includes('PM');
    const isAM = clean.toUpperCase().includes('AM');
    const timeOnly = clean.replace(/[APMapm\s]/g, '');
    const parts = timeOnly.split(':').map((v) => parseInt(v, 10));
    let hours = parts[0] || 0;
    const mins = parts[1] || 0;
    if (isPM && hours < 12) hours += 12;
    if (isAM && hours === 12) hours = 0;
    return hours * 60 + mins;
  };

  const timelines = timelineData.tm_timelines;

  // Dynamically calculate actual consecutive dispatch and unloading intervals
  const calculatedIntervals: CalculatedIntervalItem[] = [];
  for (let i = 0; i < timelines.length - 1; i++) {
    const curr = timelines[i];
    const next = timelines[i + 1];

    const currSiteIn = parseMins(curr.site_in);
    const nextSiteIn = parseMins(next.site_in);
    const currUnloadStart = parseMins(curr.unload_start);
    const nextUnloadStart = parseMins(next.unload_start);

    const dispatchInterval = Math.max(0, nextSiteIn - currSiteIn);
    const unloadingInterval = Math.max(0, nextUnloadStart - currUnloadStart);
    const recommendedInterval = unloadingInterval > 0 ? unloadingInterval : 15;
    const variance = dispatchInterval - recommendedInterval;

    let remarks = 'On schedule';
    if (variance < -5) remarks = 'Dispatched too early';
    else if (variance > 10) remarks = 'Dispatched too late';

    calculatedIntervals.push({
      from_to: `${curr.tm_no} → ${next.tm_no}`,
      dispatch_interval_mins: dispatchInterval,
      unloading_interval_mins: unloadingInterval,
      recommended_interval_mins: recommendedInterval,
      variance_mins: variance,
      remarks,
    });
  }

  const filteredIntervals = calculatedIntervals.filter((row) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return row.from_to.toLowerCase().includes(q) || row.remarks.toLowerCase().includes(q);
  });

  const totalPages = Math.max(1, Math.ceil(filteredIntervals.length / pageSize));
  const paginatedIntervals = filteredIntervals.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const previewItems = calculatedIntervals.slice(0, 6);

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 flex flex-col justify-between">
      <div>
        {/* Title */}
        <h2 className="text-xs font-bold uppercase tracking-tight mb-2 text-slate-800">
          CONSECUTIVE DISPATCH INTERVAL (RECOMMENDED VS ACTUAL)
        </h2>

        {calculatedIntervals.length === 0 ? (
          <div className="p-8 text-center text-xs italic border border-slate-200 rounded-lg bg-slate-50 text-slate-500">
            No dispatch interval records for active filters.
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200/90 rounded-md bg-white">
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] uppercase font-bold border-b border-slate-200 bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left font-bold text-slate-700">Dispatches</th>
                  <th className="px-3 py-2 text-center font-bold text-slate-700">Dispatch Interval</th>
                  <th className="px-3 py-2 text-center font-bold text-slate-700">Unloading Interval</th>
                  <th className="px-3 py-2 text-center font-bold text-slate-700">Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {previewItems.map((row, idx) => (
                  <tr key={`${row.from_to}-${idx}`} className="transition border-b border-slate-100 text-xs hover:bg-slate-50">
                    <td className="px-3 py-2 font-bold font-mono text-slate-900">{row.from_to}</td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-slate-800">{row.dispatch_interval_mins} min</td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-slate-800">{row.unloading_interval_mins} min</td>
                    <td className="px-3 py-2 text-center">
                      <span
                        className="text-[10px] font-semibold px-2 py-0.5 rounded-md border inline-block"
                        style={{
                          backgroundColor: row.remarks === 'Dispatched too early' ? '#FEF2F2' : row.remarks === 'Dispatched too late' ? '#FEF3C7' : '#ECFDF5',
                          color: row.remarks === 'Dispatched too early' ? '#B91C1C' : row.remarks === 'Dispatched too late' ? '#B45309' : '#047857',
                          borderColor: row.remarks === 'Dispatched too early' ? '#FECACA' : row.remarks === 'Dispatched too late' ? '#FDE68A' : '#A7F3D0',
                        }}
                      >
                        {row.remarks}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Informational Note */}
        <p className="text-[10px] text-slate-500 italic mt-2">
          ℹ Negative variance indicates dispatches occurred faster than site unloading capacity.
        </p>
      </div>

      {/* Footer Link */}
      {calculatedIntervals.length > 0 && (
        <div className="pt-2 border-t border-slate-100 flex items-center">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1.5 transition cursor-pointer"
          >
            <span>View full dispatch interval analysis</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Side Drawer Modal for full interval list - Clean Light Theme */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end transition-opacity duration-300"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDrawerOpen(false);
          }}
        >
          <div className="w-full max-w-4xl bg-white border-l border-slate-200 text-slate-900 flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-300">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold tracking-tight text-slate-900">
                    DISPATCH INTERVAL Vs UNLOADING INTERVAL DETAILS
                  </h2>
                  <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    {calculatedIntervals.length} Comparisons
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Consecutive vehicle dispatch pacing and site unloading capacity variance analysis
                </p>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
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
                  placeholder="Search by TM or remarks..."
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
                  ? `Matches: ${filteredIntervals.length} of ${calculatedIntervals.length}`
                  : `Total Records: ${calculatedIntervals.length}`}
              </span>
            </div>

            {/* Drawer Content Table */}
            <div className="p-5 flex-1 overflow-y-auto space-y-4">
              {calculatedIntervals.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  No dispatch interval records for active filters.
                </div>
              ) : filteredIntervals.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm italic">
                  No interval comparisons match query &quot;{searchQuery}&quot;.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                  <table className="w-full text-left text-xs text-slate-800 min-w-[700px]">
                    <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[10px]">
                      <tr>
                        <th className="px-3 py-2.5 text-left font-bold text-slate-700">From → To</th>
                        <th className="px-3 py-2.5 text-center font-bold text-slate-700">Dispatch Interval</th>
                        <th className="px-3 py-2.5 text-center font-bold text-slate-700">Unloading Interval</th>
                        <th className="px-3 py-2.5 text-center font-bold text-slate-700">Recommended</th>
                        <th className="px-3 py-2.5 text-center font-bold text-slate-700">Variance</th>
                        <th className="px-3 py-2.5 text-left font-bold text-slate-700">Remarks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-sans">
                      {paginatedIntervals.map((row, idx) => (
                        <tr key={`drawer-${row.from_to}-${idx}`} className="hover:bg-slate-50/75 transition border-b border-slate-100 text-xs">
                          <td className="px-3 py-2.5 font-bold text-slate-900 font-mono">{row.from_to}</td>
                          <td className="px-3 py-2.5 text-center text-slate-700 font-mono tabular-nums">{row.dispatch_interval_mins} min</td>
                          <td className="px-3 py-2.5 text-center text-slate-700 font-mono tabular-nums">{row.unloading_interval_mins} min</td>
                          <td className="px-3 py-2.5 text-center text-slate-700 font-mono tabular-nums">{row.recommended_interval_mins} min</td>
                          <td className={`px-3 py-2.5 text-center font-bold font-mono tabular-nums ${row.variance_mins < 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                            {row.variance_mins > 0 ? `+${row.variance_mins}` : row.variance_mins} min
                          </td>
                          <td className="px-3 py-2.5">
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border inline-block ${
                                row.remarks === 'Dispatched too early'
                                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                                  : row.remarks === 'Dispatched too late'
                                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              }`}
                            >
                              {row.remarks}
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
                        Showing <strong className="text-slate-900 font-mono">{paginatedIntervals.length}</strong> of{' '}
                        <strong className="text-slate-900 font-mono">{filteredIntervals.length}</strong> records
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

            {/* Drawer Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end items-center">
              <button
                onClick={() => setDrawerOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-md bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 transition-colors cursor-pointer"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
