import React, { useState } from 'react';
import {
  useRouteAnalysisBatchContext,
  useRouteAnalysisHistory,
  useRouteAnalysisSnapshot,
  useGenerateRouteAnalysisBatch,
  useExecuteRouteAnalysis,
} from '../../hooks/useRouteAnalysis';
import { useDashboardFilters } from '../../../site_dashboard/orchestration/DashboardFilterProvider';
import {
  RouteAnalysisMode,
  RouteAnalysisSynthesisResult,
} from './routeAnalysis.types';
import { DispatchRouteAnalysisOverviewTable } from './DispatchRouteAnalysisOverviewTable';
import { RecommendationBanner } from './RecommendationBanner';
import { CandidateComparisonMatrix } from './CandidateComparisonMatrix';
import { RouteMapVisualization } from './RouteMapVisualization';
import { TMIncidentAccessWorkspace } from './TMIncidentAccessWorkspace';
import { GoogleApiUsageIndicator } from './GoogleApiUsageIndicator';
import {
  Route,
  Clock,
  Zap,
  RefreshCw,
  Database,
  ChevronLeft,
  FileSpreadsheet,
  FileText,
  Search,
  Filter,
  Layers,
  ShieldCheck,
} from 'lucide-react';
import { env } from '../../../../config/env';

export const RouteAnalysisWorkspace: React.FC = () => {
  const { filters } = useDashboardFilters();

  // Mode Selection: NOW vs PLANNED
  const [workspaceSubTab, setWorkspaceSubTab] = useState<'DELIVERY' | 'INCIDENT'>('DELIVERY');
  const [analysisMode, setAnalysisMode] = useState<RouteAnalysisMode>('NOW');
  const [plannedTime, setPlannedTime] = useState<string>('');

  // Selected Snapshot Drill-down State (null = overview table view)
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [selectedCandidatePlantId, setSelectedCandidatePlantId] = useState<string | null>(null);

  // Status Filter & Pagination for Overview Table
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // TanStack Query Hooks
  const batchContextQuery = useRouteAnalysisBatchContext();
  const generateBatchMutation = useGenerateRouteAnalysisBatch();

  const historyQuery = useRouteAnalysisHistory({
    plant_id: filters.plant_id !== 'ALL' ? filters.plant_id : undefined,
    customer_id: filters.customer_id !== 'ALL' ? filters.customer_id : undefined,
    recommendation_status: statusFilter !== 'ALL' ? statusFilter : undefined,
    evaluation_mode: analysisMode,
    page: currentPage,
    page_size: pageSize,
  });

  const snapshotQuery = useRouteAnalysisSnapshot(selectedSnapshotId);
  const executeMutation = useExecuteRouteAnalysis();

  const batchContext = batchContextQuery.data?.data;
  const isGeneratingBatch = generateBatchMutation.isPending;

  // Overview Counts & Stats from batch context or history
  const totalErpDispatches = batchContext?.total_erp_dispatches || 0;
  const activeBatchId = batchContext?.batch_id || null;
  const totalCorridors = batchContext?.unique_route_corridors || 0;
  const analyzedSnapshots = historyQuery.data?.total_count || batchContext?.analyzed_snapshots || 0;
  const totalCount = historyQuery.data?.total_count || 0;
  const snapshots = historyQuery.data?.data || [];

  // Client-side search filtering on dispatch number, site name, customer name
  const filteredSnapshots = snapshots.filter((s) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const dNum = s.dispatch_number?.toLowerCase() || '';
    const cName = s.customer_name?.toLowerCase() || '';
    const sName = s.site_name?.toLowerCase() || '';
    const aid = s.analysis_id.toLowerCase();
    return dNum.includes(term) || cName.includes(term) || sName.includes(term) || aid.includes(term);
  });

  const countAltRecommended = batchContext?.alt_recommended_count || 0;
  const countRetainApproved = batchContext?.retain_approved_count || 0;
  const countNoDifference = batchContext?.no_difference_count || 0;
  const countMissingCoords = batchContext?.location_missing_count || 0;
  const countLiveOnly = batchContext?.live_only_count || 0;
  const countOtherOutcomes = Math.max(0, analyzedSnapshots - countAltRecommended - countRetainApproved - countNoDifference - countMissingCoords - countLiveOnly);

  // Handler: Generate Route Analysis for Batch
  const handleGenerateRouteAnalysis = () => {
    generateBatchMutation.mutate(
      {
        force_refresh: false,
        analysis_mode: analysisMode === 'PLANNED' ? 'PLANNED_DEPARTURE' : 'NOW',
        planned_departure_time: analysisMode === 'PLANNED' && plannedTime ? plannedTime : undefined,
      },
      {
        onSuccess: (res) => {
          setToastMessage(res.message || 'Batch route analysis generated successfully.');
          batchContextQuery.refetch();
          historyQuery.refetch();
          setTimeout(() => setToastMessage(null), 4000);
        },
        onError: (err) => {
          setToastMessage(`Batch generation failed: ${err.message}`);
          setTimeout(() => setToastMessage(null), 5000);
        },
      }
    );
  };

  // Handler: Re-evaluate live Google Route for currently viewed snapshot
  const handleReevaluateCurrentTraffic = () => {
    if (!selectedSnapshot) return;
    executeMutation.mutate(
      {
        site_id: selectedSnapshot.site_id,
        current_source_plant_id: selectedSnapshot.current_source_plant_id,
        analysis_mode: 'NOW',
        force_refresh_google: true,
      },
      {
        onSuccess: (res) => {
          const newId = res?.data?.analysis_id || (res as any)?.analysis_id;
          if (newId) {
            setSelectedSnapshotId(newId);
            setToastMessage('Live route re-evaluated successfully.');
            setTimeout(() => setToastMessage(null), 3000);
          }
        },
        onError: (err) => {
          setToastMessage(`Re-evaluation failed: ${err.message}`);
          setTimeout(() => setToastMessage(null), 5000);
        },
      }
    );
  };

  // Handler: XLSX / PDF Export referencing immutable snapshot analysis_id with Bearer authentication
  const handleExport = async (format: 'xlsx' | 'pdf') => {
    if (!selectedSnapshotId) return;
    try {
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      
      const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/snapshot/${selectedSnapshotId}/export/${format}${
        token ? `?token=${encodeURIComponent(token)}` : ''
      }`;
      
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      
      if (!response.ok) {
        throw new Error(`Export download failed with HTTP ${response.status}: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `route_analysis_${selectedSnapshotId.slice(0, 8)}.${format}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err: any) {
      setToastMessage(`Export download failed: ${err.message}`);
      setTimeout(() => setToastMessage(null), 5000);
    }
  };

  const selectedSnapshot: RouteAnalysisSynthesisResult | null = snapshotQuery.data?.data || null;

  return (
    <div className="space-y-6">
      {/* Top Workspace Sub-Tab Navigation - Strict Light Theme */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
        <button
          type="button"
          onClick={() => setWorkspaceSubTab('DELIVERY')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition cursor-pointer ${
            workspaceSubTab === 'DELIVERY'
              ? 'bg-white text-blue-700 border border-slate-200/90 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70 border border-transparent'
          }`}
        >
          <Layers className="w-4 h-4 text-emerald-600" />
          <span>Delivery / Site Route Analysis</span>
        </button>

        <button
          type="button"
          onClick={() => setWorkspaceSubTab('INCIDENT')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition cursor-pointer ${
            workspaceSubTab === 'INCIDENT'
              ? 'bg-amber-50 text-amber-900 border border-amber-300/90 shadow-2xs'
              : 'text-slate-600 hover:text-amber-900 hover:bg-amber-50/50 border border-transparent'
          }`}
        >
          <Route className="w-4 h-4 text-amber-600" />
          <span>TM Incident / Stuck TM Current-Traffic</span>
        </button>
      </div>

      {workspaceSubTab === 'INCIDENT' ? (
        <TMIncidentAccessWorkspace />
      ) : (
        <div className="space-y-5">
      {/* Toast notification banner */}
      {toastMessage && (
        <div className="p-3 px-4 rounded-lg bg-slate-900 text-white text-xs font-semibold shadow-md flex items-center justify-between animate-fade-in">
          <span>{toastMessage}</span>
          <button type="button" onClick={() => setToastMessage(null)} className="text-slate-400 hover:text-white font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* 1. ERP Batch & Generation Context Ribbon */}
      <div className="p-4 rounded-lg border border-slate-200/90 bg-white shadow-2xs space-y-3.5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3.5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-50 border border-blue-200/70 text-blue-700">
              <Route className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">Route Analysis Decision Support Engine</h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-bold">
                  v1.2.1 FROZEN
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Dual-evidence synthesis: Authoritative ERP T1 historical transit + Google Routes API v2 traffic
              </p>
            </div>
          </div>

          {/* Temporal Evaluation Mode Selector */}
          <div className="flex items-center p-1 rounded-lg bg-slate-100 border border-slate-200 text-xs font-semibold self-start md:self-auto">
            <button
              type="button"
              onClick={() => setAnalysisMode('NOW')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-bold transition-all ${
                analysisMode === 'NOW'
                  ? 'bg-white text-blue-700 shadow-2xs border border-slate-200/90'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Current Traffic (NOW)
            </button>
            <button
              type="button"
              onClick={() => setAnalysisMode('PLANNED')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-bold transition-all ${
                analysisMode === 'PLANNED'
                  ? 'bg-white text-blue-700 shadow-2xs border border-slate-200/90'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Planned Departure
            </button>
          </div>
        </div>

        {/* Planned Departure Controls */}
        {analysisMode === 'PLANNED' && (
          <div className="flex flex-wrap items-center gap-3 p-3 bg-blue-50/50 rounded-lg border border-blue-200/70 text-xs">
            <Clock className="w-4 h-4 text-blue-700 shrink-0" />
            <span className="font-semibold text-slate-800">Planned Departure Timestamp:</span>
            <input
              type="datetime-local"
              value={plannedTime}
              onChange={(e) => setPlannedTime(e.target.value)}
              className="bg-white border border-slate-300 rounded-md px-2.5 py-1 text-xs text-slate-800 focus:outline-none focus:border-blue-600 font-mono"
            />
            <span className="text-[11px] text-slate-500 italic">
              Uses Google Routes predictive model + historical baseline for identical time windows
            </span>
          </div>
        )}

        {/* Google Maps & Routes API Quota & Allowance Ribbon Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-2.5 px-3 rounded-lg bg-slate-50/70 border border-slate-200/80 text-xs">
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-bold text-slate-700">Google Maps Quota &amp; Allowance:</span>
            <GoogleApiUsageIndicator />
          </div>
          <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
            Authoritative monthly telemetry &bull; $200 recurring credit tracking
          </span>
        </div>

        {/* ERP Batch Operational Lineage Ribbon */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-50/80 border border-slate-200/80 text-xs">
          <div className="flex flex-wrap items-center gap-4 text-slate-600">
            <div className="flex items-center gap-1.5 font-medium">
              <Database className="w-4 h-4 text-slate-500" />
              <span>Active ERP Batch:</span>
              <strong className="text-slate-900 font-mono">{activeBatchId ? activeBatchId.slice(0, 8) : 'N/A'}</strong>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span>Total ERP Dispatches:</span>
              <strong className="text-slate-900 font-mono tabular-nums">{totalErpDispatches}</strong>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span>Unique Route Corridors:</span>
              <strong className="text-slate-900 font-mono tabular-nums">{totalCorridors}</strong>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span>Evaluation Mode:</span>
              <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold border ${
                analysisMode === 'PLANNED'
                  ? 'bg-blue-50 text-blue-800 border-blue-200'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200'
              }`}>
                {analysisMode === 'PLANNED' ? '🕒 PLANNED DEPARTURE' : '⚡ LIVE CURRENT TRAFFIC'}
              </span>
            </div>
            <div className="flex items-center gap-1.5 font-medium">
              <span>Status:</span>
              <span className="inline-flex items-center gap-1 text-emerald-700 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                GENERATED
              </span>
            </div>
          </div>

          <button
            type="button"
            disabled={isGeneratingBatch}
            onClick={handleGenerateRouteAnalysis}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-lg text-xs shadow-2xs disabled:opacity-50 transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGeneratingBatch ? 'animate-spin' : ''}`} />
            {isGeneratingBatch ? 'Generating Snapshots...' : 'Generate Route Analysis'}
          </button>
        </div>
      </div>

      {/* 2. Dispatches Overview Table or Selected Snapshot Drill-down */}
      {!selectedSnapshotId ? (
        <div className="space-y-4">
          {/* Summary KPIs Row (100% Reconciled Population Accounting) */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-lg bg-white border border-slate-200/90 shadow-2xs space-y-1">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Dispatches Analyzed</div>
              <div className="text-2xl font-extrabold text-slate-900 font-mono tabular-nums">{analyzedSnapshots}</div>
              <div className="text-[10px] text-slate-400 font-medium">Cumulative Snapshots</div>
            </div>

            <div className="p-3.5 rounded-lg bg-white border border-amber-200 shadow-2xs space-y-1">
              <div className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">No Difference</div>
              <div className="text-2xl font-extrabold text-amber-800 font-mono tabular-nums">{countNoDifference}</div>
              <div className="text-[10px] text-amber-600 font-medium">Retain Current Plant</div>
            </div>

            <div className="p-3.5 rounded-lg bg-white border border-sky-200 shadow-2xs space-y-1">
              <div className="text-[10px] font-bold text-sky-700 uppercase tracking-wider">Live Route Only</div>
              <div className="text-2xl font-extrabold text-sky-800 font-mono tabular-nums">{countLiveOnly}</div>
              <div className="text-[10px] text-sky-600 font-medium">Google Live Only (C8)</div>
            </div>

            <div className="p-3.5 rounded-lg bg-white border border-emerald-200 shadow-2xs space-y-1">
              <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Alt Recommended</div>
              <div className="text-2xl font-extrabold text-emerald-800 font-mono tabular-nums">{countAltRecommended}</div>
              <div className="text-[10px] text-emerald-600 font-medium">&gt;10 min Traffic Savings</div>
            </div>

            <div className="p-3.5 rounded-lg bg-white border border-slate-200/90 shadow-2xs space-y-1">
              <div className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">Other Outcomes</div>
              <div className="text-2xl font-extrabold text-slate-800 font-mono tabular-nums">{countOtherOutcomes}</div>
              <div className="text-[10px] text-slate-400 font-medium">No Rec / Excluded</div>
            </div>

            <div className="p-3.5 rounded-lg bg-white border border-rose-200 shadow-2xs space-y-1">
              <div className="text-[10px] font-bold text-rose-700 uppercase tracking-wider">No GPS / Coords</div>
              <div className="text-2xl font-extrabold text-rose-800 font-mono tabular-nums">{countMissingCoords}</div>
              <div className="text-[10px] text-rose-600 font-medium">Data Quality Alert (C11)</div>
            </div>
          </div>

          {/* Overview Filtering Toolbar */}
          <div className="p-3.5 rounded-lg border border-slate-200/90 bg-white shadow-2xs flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              <div className="relative w-full md:w-72">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search dispatch #, site, customer..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:border-blue-600 font-medium"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-semibold bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-600 text-slate-700"
              >
                <option value="ALL">All Decision Outcomes</option>
                <option value="RECOMMEND_ALTERNATIVE">Alternative Recommended</option>
                <option value="RECOMMEND_CURRENT_SOURCE">Retain Current Source</option>
                <option value="NO_CLEAR_DIFFERENCE">No Clear Difference</option>
                <option value="LIVE_ROUTE_ONLY">Live Route Only (C8)</option>
                <option value="HISTORICAL_COMPARISON_ONLY">Historical Only (C7)</option>
                <option value="LOCATION_DATA_MISSING">Location Data Missing</option>
              </select>

              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-semibold bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-600 text-slate-700"
              >
                <option value={25}>25 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
                <option value={200}>200 per page</option>
              </select>
            </div>

            <div className="text-xs font-medium text-slate-500 shrink-0">
              Showing <strong>{filteredSnapshots.length}</strong> of <strong>{totalCount}</strong> snapshot records
            </div>
          </div>

          {/* Dispatch Overview Table */}
          <DispatchRouteAnalysisOverviewTable
            snapshots={filteredSnapshots}
            totalCount={totalCount}
            currentPage={currentPage}
            pageSize={pageSize}
            onPageChange={(p) => setCurrentPage(p)}
            isLoading={historyQuery.isLoading}
            selectedSnapshotId={selectedSnapshotId}
            onSelectSnapshot={(id) => setSelectedSnapshotId(id)}
            analysisMode={analysisMode}
            onGenerateAnalysis={handleGenerateRouteAnalysis}
            isGenerating={isGeneratingBatch}
          />
        </div>
      ) : (
        /* Detailed Snapshot Inspection Workspace */
        <div className="space-y-5">
          {/* Top Bar: Back to Overview and Re-evaluate Action */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-lg border border-slate-200/90 bg-white shadow-2xs">
            <button
              type="button"
              data-testid="btn-back-to-overview"
              onClick={() => setSelectedSnapshotId(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold text-xs cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
              Back to Overview
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={executeMutation.isPending}
                onClick={handleReevaluateCurrentTraffic}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md font-bold text-xs bg-blue-700 hover:bg-blue-800 text-white shadow-2xs disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${executeMutation.isPending ? 'animate-spin' : ''}`} />
                Re-evaluate Current Traffic
              </button>
            </div>
          </div>

          {selectedSnapshot ? (
            <div className="space-y-5">
              {/* Executive Recommendation Banner */}
              <RecommendationBanner result={selectedSnapshot} />

              {/* WS-ROUT-7: Physical Corridor Google Route Map Visualization */}
              <RouteMapVisualization
                result={selectedSnapshot}
                selectedCandidateId={selectedCandidatePlantId}
                onSelectCandidate={(plantId) => setSelectedCandidatePlantId(plantId)}
              />

              {/* Candidate Plant Comparison Matrix */}
              <CandidateComparisonMatrix
                comparisons={selectedSnapshot.comparisons}
                currentPlantId={selectedSnapshot.current_source_plant_id}
                recommendedPlantId={selectedSnapshot.recommended_plant_id}
                selectedCandidateId={selectedCandidatePlantId}
                onSelectCandidate={(plantId) => setSelectedCandidatePlantId(plantId)}
              />

              {/* Export & Audit Bar */}
              <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-lg border border-slate-200/90 bg-white text-xs shadow-2xs">
                <div className="flex flex-wrap items-center gap-4 text-slate-500">
                  {selectedSnapshot.dispatch_number && (
                    <span className="font-mono">
                      Dispatch #: <strong className="text-slate-900 font-bold">{selectedSnapshot.dispatch_number}</strong>
                    </span>
                  )}
                  {selectedSnapshot.trip_number && (
                    <span className="font-mono">
                      Trip #: <strong className="text-slate-900 font-bold">{selectedSnapshot.trip_number}</strong>
                    </span>
                  )}
                  <span className="font-mono">
                    Analysis ID: <strong className="text-slate-800">{selectedSnapshot.analysis_id.slice(0, 8)}</strong>
                  </span>
                  <span>
                    Engine: <strong className="text-slate-800">{selectedSnapshot.engine_version || '1.2.1'}</strong>
                  </span>
                  <span>
                    Policy: <strong className="text-slate-800">{selectedSnapshot.policy_version || '1.2.1'}</strong>
                  </span>
                  <span>
                    Freshness:{' '}
                    <strong className={selectedSnapshot.is_google_fresh ? 'text-emerald-700' : 'text-amber-700'}>
                      {selectedSnapshot.google_cache_age_seconds !== undefined
                        ? Math.round(selectedSnapshot.google_cache_age_seconds)
                        : 0}
                      s ({selectedSnapshot.is_google_fresh ? 'Fresh' : 'Cached'})
                    </strong>
                  </span>
                </div>

                {/* Export Actions (WS-ROUT-5 Integration) */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    data-testid="btn-export-xlsx"
                    onClick={() => handleExport('xlsx')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-bold cursor-pointer"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                    Export XLSX
                  </button>
                  <button
                    type="button"
                    data-testid="btn-export-pdf"
                    onClick={() => handleExport('pdf')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-bold cursor-pointer"
                  >
                    <FileText className="w-3.5 h-3.5 text-rose-600" />
                    Export PDF
                  </button>
                </div>
              </div>

              {/* Operational Advisory Banner */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-600 text-[11px] leading-relaxed flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-slate-500 shrink-0" />
                <span>
                  <strong>Operational Advisory Only:</strong> This engine calculates route and transit evidence from
                  authoritative ERP history and Google Routes API estimates. Truck availability and live vehicle
                  locations are not evaluated. The final dispatch decision remains with plant operations.
                </span>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-lg border border-slate-200 bg-white">
              <div className="w-8 h-8 border-4 border-blue-700 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs font-semibold text-slate-600">Loading snapshot evidence details...</p>
            </div>
          )}
        </div>
      )}
            </div>
      )}
    </div>
  );
};
