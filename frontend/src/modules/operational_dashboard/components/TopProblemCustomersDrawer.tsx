import React, { useState, useMemo, useEffect } from 'react';
import { ProblemCustomerDTO } from '../hooks/useTopProblemCustomers';
import { X, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface TopProblemCustomersDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  customers: ProblemCustomerDTO[];
  totalCount: number;
}

export const TopProblemCustomersDrawer: React.FC<TopProblemCustomersDrawerProps> = ({
  isOpen,
  onClose,
  customers,
  totalCount,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    setCurrentPage(1);
    setSearchQuery('');
  }, [isOpen]);

  const filteredCustomers = useMemo(() => {
    if (!searchQuery.trim()) return customers;
    const q = searchQuery.toLowerCase().trim();
    return customers.filter(
      (c) =>
        c.customer_name?.toLowerCase().includes(q) ||
        c.customer_id?.toLowerCase().includes(q)
    );
  }, [customers, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredCustomers.length / pageSize));
  const paginatedCustomers = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredCustomers.slice(start, start + pageSize);
  }, [filteredCustomers, currentPage, pageSize]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end transition-opacity duration-300">
      <div className="w-full max-w-4xl bg-white border-l border-slate-200 text-slate-900 flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold tracking-tight text-slate-900">ALL PROBLEM CUSTOMERS</h2>
              <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 font-mono">
                {totalCount} Total Customers
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Full Ranked Directory of Problem Customers by Total Lost Hours (Holding &gt; 20m + Retention &gt; 10m)
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
              ? `Matches: ${filteredCustomers.length} of ${customers.length}`
              : `Total Records: ${customers.length}`}
          </span>
        </div>

        {/* Content Table */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {customers.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              No customer observations available for this scope.
            </div>
          ) : filteredCustomers.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm italic">
              No customers match query &quot;{searchQuery}&quot;.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-left text-xs text-slate-800 min-w-[700px]">
                <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[10px]">
                  <tr>
                    <th scope="col" className="px-3 py-2.5 text-center w-12">Rank</th>
                    <th scope="col" className="px-3 py-2.5">Customer</th>
                    <th scope="col" className="px-3 py-2.5 text-right">Trips</th>
                    <th scope="col" className="px-3 py-2.5 text-right">Holding (h)</th>
                    <th scope="col" className="px-3 py-2.5 text-right">Retention (h)</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-bold text-rose-700">Total Lost (h)</th>
                    <th scope="col" className="px-3 py-2.5 text-right">CEI Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {paginatedCustomers.map((c) => (
                    <tr key={c.customer_id} className="hover:bg-slate-50/75 transition-colors">
                      <td className="px-3 py-2.5 text-center text-slate-500 font-mono text-[11px]">{c.rank}</td>
                      <td className="px-3 py-2.5 font-medium text-slate-900">{c.customer_name}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-600">{c.total_trips.toLocaleString()}</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-700">{c.holding_hours.toFixed(1)}h</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-slate-700">{c.retention_hours.toFixed(1)}h</td>
                      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-rose-700 font-bold">
                        {c.total_lost_hours.toFixed(1)}h
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <span className={`px-1.5 py-0.5 rounded-md text-[11px] font-mono tabular-nums font-semibold border ${
                          c.cei >= 70 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          c.cei >= 40 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                          'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>
                          {c.cei.toFixed(1)}
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
                    Showing <strong className="text-slate-900 font-mono">{paginatedCustomers.length}</strong> of{' '}
                    <strong className="text-slate-900 font-mono">{filteredCustomers.length}</strong> records
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
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
                      className="p-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
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
