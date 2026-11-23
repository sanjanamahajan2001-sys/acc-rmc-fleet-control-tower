import React, { useState, useMemo, useEffect } from 'react';
import { ArrowRight, X, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { TMTimelineItem, TimelineData } from '../timeline/types';

interface QueueOnArrivalWidgetProps {
  timelineData: TimelineData | null;
  loading?: boolean;
}

interface QueueOnArrivalItem {
  tm_no: string;
  arrival_time: string;
  queue_on_arrival: number;
  overlapped_with: string;
}

export const QueueOnArrivalWidget: React.FC<QueueOnArrivalWidgetProps> = ({ timelineData, loading }) => {
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

  // Helper to parse standard HH:MM time strings into minutes from midnight
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

  // Compute real-time queue on arrival and overlap lists dynamically from timeline dispatches
  const calculatedItems: QueueOnArrivalItem[] = timelines.map((item: TMTimelineItem, idx: number) => {
    const currentIn = parseMins(item.site_in);
    const currentOut = parseMins(item.site_out);

    // Find all other TMs currently active on site when this TM arrived
    const activeOverlaps: string[] = [];
    timelines.forEach((other: TMTimelineItem, oIdx: number) => {
      if (idx === oIdx) return;
      const otherIn = parseMins(other.site_in);
      const otherOut = parseMins(other.site_out);
      // Overlap condition: arrived before this TM left and left after this TM arrived
      if (otherIn <= currentOut && otherOut >= currentIn) {
        activeOverlaps.push(other.tm_no);
      }
    });

    const queueCount = activeOverlaps.length > 0 ? activeOverlaps.length + 1 : 1;

    return {
      tm_no: item.tm_no,
      arrival_time: item.site_in || '09:00',
      queue_on_arrival: queueCount,
      overlapped_with: activeOverlaps.length > 0 ? activeOverlaps.join(', ') : '-',
    };
  });

  const filteredItems = calculatedItems.filter((row) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return row.tm_no.toLowerCase().includes(q) || row.overlapped_with.toLowerCase().includes(q);
  });

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / pageSize));
  const paginatedItems = filteredItems.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const previewItems = calculatedItems.slice(0, 6);

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 flex flex-col justify-between">
      <div>
        {/* Title */}
        <h2 className="text-xs font-bold uppercase tracking-tight mb-2 text-slate-800">
          QUEUE ON ARRIVAL &amp; OVERLAP
        </h2>

        {calculatedItems.length === 0 ? (
          <div className="p-8 text-center text-xs italic border border-slate-200 rounded-lg bg-slate-50 text-slate-500">
            No arrival overlap records for active filters.
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200/90 rounded-md bg-white">
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] uppercase font-bold border-b border-slate-200 bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left font-bold text-slate-700">TM No.</th>
                  <th className="px-3 py-2 text-center font-bold text-slate-700">Arrival Time</th>
                  <th className="px-3 py-2 text-center font-bold text-slate-700">Queue On Arrival<br/><span className="text-[9px] font-normal text-slate-500">(No. of TMs already at site)</span></th>
                  <th className="px-3 py-2 text-left font-bold text-slate-700">Overlapped With</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {previewItems.map((row, idx) => (
                  <tr key={`${row.tm_no}-${idx}`} className="transition border-b border-slate-100 text-xs hover:bg-slate-50">
                    <td className="px-3 py-2 font-bold font-mono text-slate-900">{row.tm_no}</td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-slate-700">{row.arrival_time}</td>
                    <td className="px-3 py-2 text-center font-bold font-mono tabular-nums text-slate-900">{row.queue_on_arrival}</td>
                    <td className="px-3 py-2 text-left font-mono text-xs truncate max-w-[180px] text-slate-600" title={row.overlapped_with}>
                      {row.overlapped_with}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer Link */}
      {calculatedItems.length > 0 && (
        <div className="pt-2 border-t border-slate-100 flex items-center">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1.5 transition cursor-pointer"
          >
            <span>View full overlap details</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Side Drawer Modal for full overlap list - Clean Light Theme */}
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
                    QUEUE ON ARRIVAL &amp; OVERLAP DETAILS
                  </h2>
                  <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    {calculatedItems.length} Dispatches
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Full arrival queue and concurrent vehicle overlap analysis for active plant and customer selection
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
                  placeholder="Search by TM number..."
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
                  ? `Matches: ${filteredItems.length} of ${calculatedItems.length}`
                  : `Total Records: ${calculatedItems.length}`}
              </span>
            </div>

            {/* Drawer Content Table */}
            <div className="p-5 flex-1 overflow-y-auto space-y-4">
              {calculatedItems.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  No arrival overlap records for active filters.
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm italic">
                  No arrival overlap records match query &quot;{searchQuery}&quot;.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                  <table className="w-full text-left text-xs text-slate-800 min-w-[700px]">
                    <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[10px]">
                      <tr>
                        <th className="px-3 py-2.5 text-left font-bold text-slate-700">TM No.</th>
                        <th className="px-3 py-2.5 text-center font-bold text-slate-700">Arrival Time</th>
                        <th className="px-3 py-2.5 text-center font-bold text-slate-700">Queue On Arrival<br/><span className="text-[9px] font-normal text-slate-500">(No. of TMs already at site)</span></th>
                        <th className="px-3 py-2.5 text-left font-bold text-slate-700">Overlapped With</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-sans">
                      {paginatedItems.map((row, idx) => (
                        <tr key={`drawer-${row.tm_no}-${idx}`} className="hover:bg-slate-50/75 transition border-b border-slate-100 text-xs">
                          <td className="px-3 py-2.5 font-bold text-slate-900 font-mono">{row.tm_no}</td>
                          <td className="px-3 py-2.5 text-center text-slate-700 font-mono tabular-nums">{row.arrival_time}</td>
                          <td className="px-3 py-2.5 text-center font-bold text-blue-700 font-mono tabular-nums">{row.queue_on_arrival}</td>
                          <td className="px-3 py-2.5 text-left text-slate-700 font-mono">{row.overlapped_with}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* 10-Row Pagination Bar */}
                  {totalPages > 1 && (
                    <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs text-slate-600">
                      <div>
                        Showing <strong className="text-slate-900 font-mono">{paginatedItems.length}</strong> of{' '}
                        <strong className="text-slate-900 font-mono">{filteredItems.length}</strong> records
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
