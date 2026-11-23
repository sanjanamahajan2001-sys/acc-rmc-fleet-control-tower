import React, { useState } from 'react';
import { useDispatchCustomerReport, CustomerVehicleReportDTO } from '../hooks/useDispatchCustomerReport';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { ChevronDown, ChevronUp, AlertTriangle, ChevronLeft, ChevronRight, UserCheck, MapPin } from 'lucide-react';
import { IconUserGroup, IconTransitMixer } from '../../../components/icons/LinealColorIcons';

export const CustomerVehicleReportWidget: React.FC = () => {
  const { data, loading, error, status } = useDispatchCustomerReport();
  const [expandedCustomerCode, setExpandedCustomerCode] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 5;

  const toggleExpand = (customerCode: string) => {
    setExpandedCustomerCode((prev) => (prev === customerCode ? null : customerCode));
  };

  if (loading && (!data || data.length === 0)) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs min-h-[300px] animate-pulse">
        <div className="h-5 bg-slate-100 rounded w-1/4 mb-4"></div>
        <div className="space-y-3">
          <div className="h-14 bg-slate-50 rounded-xl"></div>
          <div className="h-14 bg-slate-50 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs min-h-[300px] flex flex-col justify-center items-center text-center">
        <AlertTriangle className="w-6 h-6 text-rose-500 mb-2" />
        <h4 className="text-xs font-semibold text-rose-700">Failed to load customer report</h4>
        <p className="text-[11px] text-slate-500 max-w-xs mt-1">{error}</p>
      </div>
    );
  }

  const reports = data || [];
  const isNoObs = status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || reports.length === 0;

  const totalPages = Math.max(1, Math.ceil(reports.length / pageSize));
  const paginatedReports = reports.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg shadow-2xs overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/70">
        <div>
          <div className="flex items-center gap-2">
            <IconUserGroup className="w-4 h-4" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">Customer Report &amp; Vehicle Matrix</h3>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Relational dispatch breakdown by client, assigned mixer trucks, trip volumes, and on-site turnaround
          </p>
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Total Clients: <strong className="text-slate-900 font-mono tabular-nums">{reports.length.toLocaleString('en-IN')}</strong>
        </div>
      </div>

      {/* List Content */}
      <div className="p-4">
        {isNoObs ? (
          <div className="py-14 text-center space-y-2">
            <div className="text-xs font-semibold text-slate-600">NO OBSERVATIONS</div>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              No customer dispatch reports available for active filters.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {paginatedReports.map((c: CustomerVehicleReportDTO) => {
              const isExpanded = expandedCustomerCode === c.customer_code;
              const dispatchesCount = c.total_dispatches ?? 0;
              const volumeM3 = c.total_volume_m3 ?? 0;
              const dasScore = c.das_score_pct ?? 0;
              const holdingMins = c.avg_holding_mins ?? 0;
              const retentionMins = c.avg_retention_mins ?? 0;
              const vehicles = c.vehicles ?? [];

              return (
                <div
                  key={c.customer_code}
                  className="border border-slate-200/80 rounded-lg bg-white overflow-hidden transition-all hover:border-slate-300"
                >
                  {/* Customer Card Summary Row */}
                  <div
                    onClick={() => toggleExpand(c.customer_code)}
                    className="p-3 cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50 hover:bg-slate-100/60 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-md bg-slate-100 border border-slate-200/90 flex items-center justify-center text-xs font-bold text-slate-700 shrink-0">
                        {(c.customer_code || 'CU').slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-slate-900">{c.customer_name}</h4>
                          <span className="text-[10px] text-slate-400 font-mono">({c.customer_code})</span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-0.5 font-sans">
                          <span><strong>{dispatchesCount.toLocaleString('en-IN')}</strong> trips</span>
                          <span>·</span>
                          <span><strong>{volumeM3.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</strong> m³</span>
                          <span>·</span>
                          <span>DAS Score: <strong className="text-blue-700 font-mono tabular-nums">{dasScore.toFixed(1)}%</strong></span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-5">
                      <div className="text-right text-xs">
                        <div className="text-[10px] uppercase font-bold text-slate-400">Avg Hold / Ret</div>
                        <div className="font-mono font-semibold text-slate-900 tabular-nums">
                          <span className="text-amber-700">{holdingMins.toFixed(1)}m</span> / <span className="text-rose-700">{retentionMins.toFixed(1)}m</span>
                        </div>
                      </div>
                      <div className="text-slate-400">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>

                  {/* Vehicle Matrix (Expandable) */}
                  {isExpanded && (
                    <div className="p-3.5 border-t border-slate-100 bg-white">
                      <div className="pb-2.5 flex items-center justify-between text-[10.5px] font-bold uppercase tracking-wider text-slate-600">
                        <span className="flex items-center gap-1.5">
                          <IconTransitMixer className="w-4 h-4" />
                          <span>Assigned Mixer Vehicles ({vehicles.length})</span>
                        </span>
                        <span className="font-mono text-[10px] text-slate-400">Vehicle Turnaround Lineage</span>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-slate-50 text-[10px] font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                              <th scope="col" className="py-2 px-3">Vehicle ID</th>
                              <th scope="col" className="py-2 px-3">Driver Name</th>
                              <th scope="col" className="py-2 px-3">Plant Site</th>
                              <th scope="col" className="py-2 px-3 text-right">Trips</th>
                              <th scope="col" className="py-2 px-3 text-right">Volume (m³)</th>
                              <th scope="col" className="py-2 px-3 text-right">Hold</th>
                              <th scope="col" className="py-2 px-3 text-right">Ret</th>
                              <th scope="col" className="py-2 px-3 text-right">DAS %</th>
                              <th scope="col" className="py-2 px-3 text-center">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
                            {vehicles.map((v) => (
                              <tr key={v.vehicle_id} className="hover:bg-slate-50/80 transition-colors">
                                <td className="py-2 px-3 font-bold text-blue-700 hover:underline cursor-pointer">
                                  {v.vehicle_id}
                                </td>
                                <td className="py-2 px-3 font-sans text-slate-800">
                                  <div className="flex items-center gap-1">
                                    <UserCheck className="w-3 h-3 text-slate-400" />
                                    <span>{v.driver_name}</span>
                                  </div>
                                </td>
                                <td className="py-2 px-3 font-sans text-slate-600">
                                  <div className="flex items-center gap-1">
                                    <MapPin className="w-3 h-3 text-slate-400" />
                                    <span>{v.plant_code}</span>
                                  </div>
                                </td>
                                <td className="py-2 px-3 text-right font-bold text-slate-900 tabular-nums">
                                  {v.trips_count}
                                </td>
                                <td className="py-2 px-3 text-right text-slate-600 tabular-nums">
                                  {(v.volume_m3 ?? 0).toFixed(1)}
                                </td>
                                <td className="py-2 px-3 text-right font-semibold text-amber-700 tabular-nums">
                                  {(v.avg_holding_mins ?? 0).toFixed(1)}m
                                </td>
                                <td className="py-2 px-3 text-right font-semibold text-rose-700 tabular-nums">
                                  {(v.avg_retention_mins ?? 0).toFixed(1)}m
                                </td>
                                <td className="py-2 px-3 text-right font-bold text-slate-900 tabular-nums">
                                  {(v.das_score_pct ?? 0).toFixed(1)}%
                                </td>
                                <td className="py-2 px-3 text-center">
                                  <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                                    v.status === 'Optimal'
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : v.status === 'Warning'
                                      ? 'bg-amber-50 text-amber-700 border-amber-200'
                                      : 'bg-rose-50 text-rose-700 border-rose-200'
                                  }`}>
                                    {v.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination Footer */}
      {!isNoObs && !loading && !error && (
        <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500">
          <div>
            Showing <strong className="text-slate-900">{paginatedReports.length}</strong> of{' '}
            <strong className="text-slate-900 font-mono tabular-nums">{reports.length.toLocaleString('en-IN')}</strong> client reports
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono font-medium px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
