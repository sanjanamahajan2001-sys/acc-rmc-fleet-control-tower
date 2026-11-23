import React, { useState, useMemo, useEffect } from 'react';
import { TMDetailsTable } from './TMDetailsTable';
import { TMDetailItem } from './TMDetailsRow';
import { X, ArrowRight, Search, ChevronLeft, ChevronRight } from 'lucide-react';

export interface TMDetailsContainerData {
  total_count: number;
  page: number;
  page_size: number;
  items: TMDetailItem[];
}

interface TMDetailsContainerProps {
  data: TMDetailsContainerData | null;
  loading?: boolean;
}

export const TMDetailsContainer: React.FC<TMDetailsContainerProps> = ({ data, loading }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tmSearch, setTmSearch] = useState('');
  const [drawerPage, setDrawerPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    setDrawerPage(1);
    setTmSearch('');
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

  const allItems = data?.items || [];

  const filteredDrawerItems = useMemo(() => {
    if (!tmSearch.trim()) return allItems;
    const q = tmSearch.toLowerCase().trim();
    return allItems.filter(
      (item) =>
        item.tm_no?.toLowerCase().includes(q) ||
        item.vehicle_plate?.toLowerCase().includes(q) ||
        item.dispatch_id?.toLowerCase().includes(q)
    );
  }, [allItems, tmSearch]);

  const totalDrawerPages = Math.max(1, Math.ceil(filteredDrawerItems.length / pageSize));
  const paginatedDrawerItems = useMemo(() => {
    const start = (drawerPage - 1) * pageSize;
    return filteredDrawerItems.slice(start, start + pageSize);
  }, [filteredDrawerItems, drawerPage, pageSize]);

  if (loading || !data) {
    return (
      <div className="bg-white rounded-lg border border-slate-200/90 p-4 shadow-sm animate-pulse space-y-3">
        <div className="h-4 w-48 bg-slate-200 rounded" />
        <div className="h-44 w-full bg-slate-100 rounded-lg" />
      </div>
    );
  }

  const previewItems = data.items.slice(0, 6);

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 flex flex-col justify-between">
      <div>
        {/* Widget Title */}
        <h2 className="text-xs font-bold uppercase tracking-tight mb-2 text-slate-800">
          TM DETAILS <span className="font-normal text-slate-500">(HOLDING &amp; RETENTION)</span>
        </h2>

        {data.items.length === 0 ? (
          <div className="p-8 text-center text-xs italic border border-slate-200 rounded-lg bg-slate-50 text-slate-500">
            No dispatch details recorded for active filters.
          </div>
        ) : (
          <TMDetailsTable items={previewItems} />
        )}
      </div>

      {/* Footer Link */}
      {data.items.length > 0 && (
        <div className="pt-2 border-t border-slate-100 flex items-center">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1.5 transition cursor-pointer"
          >
            <span>View all TMs for this site</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Side Drawer Modal for full TM list - Clean Light Theme */}
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
                    TM DETAILS (HOLDING &amp; RETENTION)
                  </h2>
                  <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    {allItems.length} Dispatches
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Full dispatch timeline breakdown for active plant and customer selection
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
                  value={tmSearch}
                  onChange={(e) => {
                    setTmSearch(e.target.value);
                    setDrawerPage(1);
                  }}
                  placeholder="Search by TM number..."
                  className="w-full pl-8 pr-7 py-1.5 rounded-md border border-slate-200 bg-white text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700"
                />
                {tmSearch && (
                  <button
                    onClick={() => {
                      setTmSearch('');
                      setDrawerPage(1);
                    }}
                    className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <span className="text-[11px] font-mono tabular-nums text-slate-500">
                {tmSearch
                  ? `Matches: ${filteredDrawerItems.length} of ${allItems.length}`
                  : `Total Records: ${allItems.length}`}
              </span>
            </div>

            {/* Drawer Content Table */}
            <div className="p-5 flex-1 overflow-y-auto space-y-4">
              {allItems.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  No dispatch details recorded for active filters.
                </div>
              ) : filteredDrawerItems.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm italic">
                  No TM records match query &quot;{tmSearch}&quot;.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                  <TMDetailsTable items={paginatedDrawerItems} isDark={false} />

                  {/* 10-Row Pagination Bar */}
                  {totalDrawerPages > 1 && (
                    <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs text-slate-600">
                      <div>
                        Showing <strong className="text-slate-900 font-mono">{paginatedDrawerItems.length}</strong> of{' '}
                        <strong className="text-slate-900 font-mono">{filteredDrawerItems.length}</strong> records
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => setDrawerPage((p) => Math.max(1, p - 1))}
                          disabled={drawerPage <= 1}
                          className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                          title="Previous Page"
                        >
                          <ChevronLeft className="w-3.5 h-3.5" />
                        </button>
                        <span className="font-mono text-[11px] px-1.5">
                          Page {drawerPage} of {totalDrawerPages}
                        </span>
                        <button
                          onClick={() => setDrawerPage((p) => Math.min(totalDrawerPages, p + 1))}
                          disabled={drawerPage >= totalDrawerPages}
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
