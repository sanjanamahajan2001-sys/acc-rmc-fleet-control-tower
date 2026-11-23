import React from 'react';
import {
  RouteAnalysisSnapshotItem,
} from './routeAnalysis.types';
import {
  Star,
  Clock,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldAlert,
  ChevronRight,
  ChevronLeft,
  Route,
  RefreshCw,
} from 'lucide-react';

interface Props {
  snapshots: RouteAnalysisSnapshotItem[];
  totalCount: number;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  isLoading: boolean;
  selectedSnapshotId: string | null;
  onSelectSnapshot: (analysisId: string) => void;
  analysisMode: 'NOW' | 'PLANNED';
  onGenerateAnalysis: () => void;
  isGenerating: boolean;
}

export const DispatchRouteAnalysisOverviewTable: React.FC<Props> = ({
  snapshots,
  totalCount,
  currentPage,
  pageSize,
  onPageChange,
  isLoading,
  selectedSnapshotId,
  onSelectSnapshot,
  analysisMode,
  onGenerateAnalysis,
  isGenerating,
}) => {
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  if (isLoading && snapshots.length === 0) {
    return (
      <div className="p-12 text-center rounded-lg border border-slate-200 bg-white">
        <div className="w-8 h-8 border-4 border-blue-700 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs font-semibold text-slate-600">Loading route snapshot history...</p>
      </div>
    );
  }

  if (snapshots.length === 0) {
    return (
      <div className="p-12 text-center rounded-lg border border-dashed border-slate-300 bg-white">
        <div className="p-3 bg-slate-50 text-slate-400 rounded-lg w-fit mx-auto mb-3">
          <Route className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-800 mb-1">No Route Analysis Snapshots Found</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
          Route analysis has not been generated for the current active ERP batch or filter criteria. Click below to
          evaluate the complete dispatch route population.
        </p>
        {onGenerateAnalysis && (
          <button
            type="button"
            disabled={isGenerating}
            onClick={onGenerateAnalysis}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold rounded-lg shadow-2xs disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
            {isGenerating ? 'Analyzing Routes...' : 'Generate Route Analysis'}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white shadow-2xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[10.5px]">
              <th className="py-3 px-4">Analysis / Dispatch #</th>
              <th className="py-3 px-3">Evaluation Mode</th>
              <th className="py-3 px-3">Customer</th>
              <th className="py-3 px-3">Destination Site</th>
              <th className="py-3 px-3">Approved Plant</th>
              <th className="py-3 px-3">Recommended Plant</th>
              <th className="py-3 px-3 text-center">Decision Outcome</th>
              <th className="py-3 px-3 text-center">Case Code</th>
              <th className="py-3 px-3 text-center">Freshness</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {snapshots.map((item) => {
              const isSelected = selectedSnapshotId === item.analysis_id;
              const outcome = item.recommendation_status;
              const caseCode =
                (item as any).case_category ||
                (item as any).historical_evidence_payload?.case_category ||
                (outcome === 'RECOMMEND_ALTERNATIVE' ? 'C2/C3 ALT RECOMMENDED' : 'C8 LIVE ROUTE ONLY');

              let statusBadge = (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                  <CheckCircle2 className="w-3 h-3" /> No Difference
                </span>
              );

              if (outcome === 'RECOMMEND_ALTERNATIVE') {
                statusBadge = (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                    <Star className="w-3 h-3 fill-emerald-600 text-emerald-600" /> Alt Recommended
                  </span>
                );
              } else if (outcome === 'RECOMMEND_CURRENT_SOURCE') {
                statusBadge = (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                    <CheckCircle2 className="w-3 h-3" /> Retain Approved
                  </span>
                );
              } else if (outcome === 'HISTORICAL_COMPARISON_ONLY' || item.failure_reason_code === 'C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED') {
                statusBadge = (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-orange-50 text-orange-800 border border-orange-200">
                    <Clock className="w-3 h-3" /> Historical Only
                  </span>
                );
              } else if (outcome === 'LIVE_ROUTE_ONLY' || item.failure_reason_code === 'C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT') {
                statusBadge = (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-sky-50 text-sky-800 border border-sky-200">
                    <Info className="w-3 h-3" /> Live Only
                  </span>
                );
              } else if (outcome === 'LOCATION_DATA_MISSING' || item.failure_reason_code === 'LOCATION_DATA_MISSING') {
                statusBadge = (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200">
                    <ShieldAlert className="w-3 h-3" /> No Coords
                  </span>
                );
              }

              const rowClass = isSelected
                ? 'bg-blue-50/70 font-medium'
                : outcome === 'RECOMMEND_ALTERNATIVE'
                ? 'bg-emerald-50/30 hover:bg-emerald-50/50'
                : 'hover:bg-slate-50/80';

              const isPlanned = item.analysis_mode === 'PLANNED_DEPARTURE' || Boolean(item.planned_departure_time);

              return (
                <tr key={item.analysis_id} className={`transition-colors ${rowClass}`}>
                  {/* Analysis ID / Dispatch Number */}
                  <td className="py-2.5 px-4 font-mono text-slate-900">
                    <div className="flex items-center gap-1.5">
                      {outcome === 'RECOMMEND_ALTERNATIVE' && (
                        <Star className="w-3.5 h-3.5 text-emerald-600 fill-emerald-500 shrink-0" />
                      )}
                      <div>
                        <div className="font-bold text-slate-900">
                          {item.dispatch_number ? `DSP #${item.dispatch_number}` : item.analysis_id.slice(0, 8)}
                        </div>
                        {item.trip_number && (
                          <div className="text-[10px] text-slate-500 font-mono">Trip #{item.trip_number}</div>
                        )}
                        {item.dispatch_number && (
                          <div className="text-[9.5px] text-slate-400 font-mono">ID: {item.analysis_id.slice(0, 8)}</div>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Evaluation Mode Indicator */}
                  <td className="py-2.5 px-3">
                    {isPlanned ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                        <Clock className="w-3 h-3 text-blue-700" />
                        Planned
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <Zap className="w-3 h-3 text-emerald-600" />
                        Live Now
                      </span>
                    )}
                  </td>

                  {/* Customer */}
                  <td className="py-2.5 px-3 text-slate-700">
                    {item.customer_name ? (
                      <>
                        <div className="font-semibold text-slate-900">{item.customer_name}</div>
                        {item.customer_code && (
                          <div className="text-[10px] text-slate-400 font-mono">({item.customer_code})</div>
                        )}
                      </>
                    ) : (
                      <span className="inline-block px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-medium">
                        Data Missing
                      </span>
                    )}
                  </td>

                  {/* Destination Site */}
                  <td className="py-2.5 px-3 text-slate-700">
                    {item.site_name ? (
                      <>
                        <div className="font-semibold text-slate-900">{item.site_name}</div>
                        {item.site_code && (
                          <div className="text-[10px] text-slate-400 font-mono">({item.site_code})</div>
                        )}
                      </>
                    ) : (
                      <span className="inline-block px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-medium">
                        Data Missing
                      </span>
                    )}
                  </td>

                  {/* Approved Origin Plant */}
                  <td className="py-2.5 px-3 text-slate-800 font-medium">
                    {item.current_source_plant_name || item.current_source_plant_code || (
                      <span className="inline-block px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-medium">
                        Data Missing
                      </span>
                    )}
                  </td>

                  {/* Recommended Plant */}
                  <td className="py-2.5 px-3">
                    {item.recommended_plant_name ? (
                      <span className="font-bold text-emerald-800">
                        {item.recommended_plant_name}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>

                  {/* Decision Outcome */}
                  <td className="py-2.5 px-3 text-center">{statusBadge}</td>

                  {/* Case Code */}
                  <td className="py-2.5 px-3 text-center">
                    <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                      {caseCode}
                    </span>
                  </td>

                  {/* Freshness */}
                  <td className="py-2.5 px-3 text-center text-[10.5px] font-mono">
                    {item.is_cached_result ? (
                      <span className="text-amber-700 font-semibold">Cached ({Math.round(item.data_freshness_seconds)}s)</span>
                    ) : (
                      <span className="text-emerald-700 font-bold">Fresh</span>
                    )}
                  </td>

                  {/* View Details Action */}
                  <td className="py-2.5 px-4 text-right">
                    <button
                      type="button"
                      data-testid={`btn-view-analysis-${item.analysis_id}`}
                      onClick={() => onSelectSnapshot(item.analysis_id)}
                      className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-bold transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-blue-700 text-white shadow-2xs'
                          : 'bg-white hover:bg-slate-50 text-blue-700 border border-slate-200/90'
                      }`}
                    >
                      <span>View Analysis</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-slate-200 bg-slate-50/70 text-xs text-slate-600">
          <div>
            Showing <strong className="text-slate-900">{(currentPage - 1) * pageSize + 1}</strong> to{' '}
            <strong className="text-slate-900">{Math.min(currentPage * pageSize, totalCount)}</strong> of{' '}
            <strong className="text-slate-900 font-mono tabular-nums">{totalCount}</strong> records
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => onPageChange(currentPage - 1)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed font-medium shadow-2xs"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Previous
            </button>

            <span className="px-2 font-semibold text-slate-700">
              Page {currentPage} of {totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => onPageChange(currentPage + 1)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed font-medium shadow-2xs"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
