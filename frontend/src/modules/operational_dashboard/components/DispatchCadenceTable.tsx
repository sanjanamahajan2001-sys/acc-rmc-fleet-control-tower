import { formatDisplayDate } from '../../../utils/date';
import React, { useState, useMemo } from 'react';
import { useDispatchCadence, DispatchCadenceRecordDTO } from '../hooks/useDispatchCadence';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { AlertTriangle, ArrowUpDown, ChevronLeft, ChevronRight, Search, X } from 'lucide-react';
import { IconCycleStopwatch } from '../../../components/icons/LinealColorIcons';

export const DispatchCadenceTable: React.FC = () => {
  const { data, loading, error, status } = useDispatchCadence();

  const [sortField, setSortField] = useState<keyof DispatchCadenceRecordDTO>('dispatch_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  const handleSort = (field: keyof DispatchCadenceRecordDTO) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
    setCurrentPage(1);
  };

  const sortedData = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];
      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortOrder === 'asc' ? valA - valB : valB - valA;
      }
      return sortOrder === 'asc'
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [data, sortField, sortOrder]);

  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) return sortedData;
    const q = searchQuery.toLowerCase().trim();
    return sortedData.filter(
      (d) =>
        d.dispatch_number?.toLowerCase().includes(q) ||
        d.customer_name?.toLowerCase().includes(q) ||
        d.plant_code?.toLowerCase().includes(q) ||
        d.vehicle_id?.toLowerCase().includes(q) ||
        d.driver_name?.toLowerCase().includes(q) ||
        d.cadence_recommendation?.toLowerCase().includes(q)
    );
  }, [sortedData, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize));
  const paginatedData = filteredData.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const isNoObs = status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || !data || data.length === 0;

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg shadow-2xs overflow-hidden">
      {/* Table Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/70">
        <div>
          <div className="flex items-center gap-2">
            <IconCycleStopwatch className="w-4 h-4" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">Dispatch Cadence &amp; Interval Variance Log</h3>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Trip departure gap sequence, interval variance from target, and automated pacing recommendations
          </p>
        </div>

        {/* Search Bar & Total Counter */}
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search dispatch, customer, vehicle..."
              className="pl-8 pr-7 py-1.5 rounded-md border border-slate-200 bg-white text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700 w-56 sm:w-64 shadow-2xs"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <div className="text-xs text-slate-500 font-medium whitespace-nowrap">
            {searchQuery ? (
              <span>Matches: <strong className="text-slate-900 font-mono tabular-nums">{filteredData.length}</strong></span>
            ) : (
              <span>Total: <strong className="text-slate-900 font-mono tabular-nums">{sortedData.length.toLocaleString('en-IN')}</strong></span>
            )}
          </div>
        </div>
      </div>

      {/* Body Content */}
      <div className="p-4">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-2">
            <div className="w-6 h-6 border-2 border-blue-700 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500">Loading dispatch cadence records...</span>
          </div>
        ) : error ? (
          <div className="py-12 text-center space-y-2">
            <div className="text-xs font-semibold flex items-center justify-center gap-2 text-rose-600">
              <AlertTriangle className="w-4 h-4" />
              <span>Failed to load cadence table: {error}</span>
            </div>
          </div>
        ) : isNoObs ? (
          <div className="py-14 text-center space-y-2">
            <div className="text-xs font-semibold text-slate-600">NO OBSERVATIONS</div>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              No dispatch cadence observations available for active filters.
            </p>
          </div>
        ) : filteredData.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 italic">
            No dispatch cadence records match query &quot;{searchQuery}&quot;.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-[10.5px] font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                  <th scope="col" className="py-2.5 px-3 cursor-pointer hover:text-slate-900" onClick={() => handleSort('dispatch_number')}>
                    <div className="flex items-center gap-1">
                      <span>Dispatch #</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th scope="col" className="py-2.5 px-3 cursor-pointer hover:text-slate-900" onClick={() => handleSort('dispatch_date')}>
                    <div className="flex items-center gap-1">
                      <span>Date / Time Out</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th scope="col" className="py-2.5 px-3">Plant &amp; Customer</th>
                  <th scope="col" className="py-2.5 px-3">Vehicle &amp; Driver</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Gap</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Variance</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Holding</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Retention</th>
                  <th scope="col" className="py-2.5 px-3 text-center">SLA Status</th>
                  <th scope="col" className="py-2.5 px-3">Pacing Recommendation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
                {paginatedData.map((d) => (
                  <tr key={d.dispatch_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-bold text-blue-700 hover:underline cursor-pointer">
                      {d.dispatch_number}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="font-semibold text-slate-900">{formatDisplayDate(d.dispatch_date)}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{d.time_out || '—'}</div>
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="font-semibold text-slate-800">{d.plant_code}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-[160px]" title={d.customer_name}>
                        {d.customer_name}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="font-semibold text-slate-800">{d.vehicle_id}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-[140px]" title={d.driver_name}>
                        {d.driver_name}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900 tabular-nums">
                      {d.interval_mins > 0 ? `${d.interval_mins.toFixed(1)}m` : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-slate-600 tabular-nums">
                      {d.variance_mins > 0 ? `±${d.variance_mins.toFixed(1)}m` : '0.0m'}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-amber-700 tabular-nums">
                      {d.holding_mins.toFixed(1)}m
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-rose-700 tabular-nums">
                      {d.retention_mins.toFixed(1)}m
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                        d.sla_status === 'ON_SCHEDULE'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {d.sla_status === 'ON_SCHEDULE' ? 'ON TIME' : 'DELAYED'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-sans text-xs text-slate-600">
                      {d.cadence_recommendation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination Footer */}
      {!isNoObs && !loading && !error && filteredData.length > 0 && (
        <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500">
          <div>
            Showing <strong className="text-slate-900">{paginatedData.length}</strong> of{' '}
            <strong className="text-slate-900 font-mono tabular-nums">{filteredData.length.toLocaleString('en-IN')}</strong> records
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono font-medium px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
