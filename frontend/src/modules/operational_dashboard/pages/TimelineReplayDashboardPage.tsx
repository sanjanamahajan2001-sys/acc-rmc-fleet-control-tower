import { formatDisplayDate } from '../../../utils/date';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import React, { useState, useEffect } from 'react';
import {
  fetchTimelineReplayDispatches,
  fetchDispatchTimelineDetail,
  DispatchReplayListItem,
  DispatchTimelineReplayDetail,
} from '../api/timelineReplayApi';
import {
  useDashboardFilters,
  DashboardFilterProvider,
} from '../../site_dashboard/orchestration/DashboardFilterProvider';
import {
  DashboardSyncProvider,
} from '../../site_dashboard/orchestration/DashboardSyncProvider';

// Icons & Sub-Components
import {
  SquarePlay,
  Clock,
  Activity,
  AlertCircle,
  FileText,
  Calendar,
  Building2,
  User,
  Truck,
  Database,
          } from 'lucide-react';
import { ReplayControlToolbar } from '../components/ReplayControlToolbar';
import { DispatchLifecycleEventList } from '../components/DispatchLifecycleEventList';
import { TimelineSpatialContextPanel } from '../components/TimelineSpatialContextPanel';

export const TimelineReplayDashboardContent: React.FC = () => {
  const { filters, plantOptions, customerOptions } = useDashboardFilters();

  // Primary State
  const [dispatches, setDispatches] = useState<DispatchReplayListItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const pageSize = 50;
  const [queueLoading, setQueueLoading] = useState<boolean>(true);
  const [queueError, setQueueError] = useState<string | null>(null);

  // Selected Detail State
  const [selectedDispatchId, setSelectedDispatchId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DispatchTimelineReplayDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Playback Control State
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);

  // Helper resolvers for friendly plant/customer names
  const resolvePlantName = (id: string | null) => {
    if (!id) return 'Unknown Plant';
    const found = plantOptions.find((p) => p.id === id);
    return found ? found.name : id.substring(0, 8);
  };

  const resolveCustomerName = (id: string | null) => {
    if (!id) return 'Unknown Customer';
    const found = customerOptions.find((c) => c.id === id);
    return found ? found.name : id.substring(0, 8);
  };

  // 1. Fetch Dispatch Queue List based on Scope Filters
  const loadDispatches = async () => {
    try {
      setQueueLoading(true);
      setQueueError(null);

      const plantFilter = filters.plant_id === 'ALL' ? undefined : filters.plant_id;
      const customerFilter = filters.customer_id === 'ALL' ? undefined : filters.customer_id;

      const resp = await fetchTimelineReplayDispatches({
        plant_id: plantFilter,
        customer_id: customerFilter,
        page,
        page_size: pageSize,
      });

      setDispatches(resp.items);
      setTotalCount(resp.total_count);

      // Auto-select first dispatch if list returns items and none currently selected
      if (resp.items.length > 0 && !selectedDispatchId) {
        setSelectedDispatchId(resp.items[0].dispatch_id);
      }
    } catch (err: any) {
      console.error('Failed to load timeline replay dispatch queue:', err);
      setQueueError('Failed to load dispatch queue from backend API.');
    } finally {
      setQueueLoading(false);
    }
  };

  useEffect(() => {
    loadDispatches();
  }, [filters.plant_id, filters.customer_id, page]);



  // 2. Fetch Detailed Timeline Replay Data when Selected Dispatch Changes
  useEffect(() => {
    if (!selectedDispatchId) {
      setDetail(null);
      return;
    }

    const loadDetail = async () => {
      try {
        setDetailLoading(true);
        setDetailError(null);
        setIsPlaying(false);
        setCurrentStepIndex(0);

        const data = await fetchDispatchTimelineDetail(selectedDispatchId);
        setDetail(data);
      } catch (err: any) {
        console.error('Failed to load dispatch timeline detail:', err);
        setDetailError('Failed to reconstruct dispatch timeline digital twin.');
      } finally {
        setDetailLoading(false);
      }
    };

    loadDetail();
  }, [selectedDispatchId]);

  // 3. Playback Timer Effect for Lifecycle Milestones
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isPlaying && detail && detail.lifecycle_events.length > 0) {
      const intervalMs = Math.max(250, 1500 / playbackSpeed);

      timer = setInterval(() => {
        setCurrentStepIndex((prevStep) => {
          if (prevStep >= detail.lifecycle_events.length - 1) {
            setIsPlaying(false);
            return prevStep;
          }
          return prevStep + 1;
        });
      }, intervalMs);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, playbackSpeed, detail]);

  const handlePlayToggle = () => {
    if (!detail || detail.lifecycle_events.length === 0) return;
    if (currentStepIndex >= detail.lifecycle_events.length - 1) {
      setCurrentStepIndex(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentStepIndex(0);
  };

  // Helper for operational date formatting
  const formatOperationalDate = (dateStr: string | null) => {
    return formatDisplayDate(dateStr);
  };

  // Safe Phase Durations calculation
  const getPhaseBreakdown = () => {
    if (!detail || !detail.lifecycle_events) {
      return { t1: null, t2a: null, t2b: null, t3: null };
    }
    const events = detail.lifecycle_events;

    const findDuration = (type: string) => {
      const found = events.find((e) => e.event_type === type);
      return found ? found.duration_mins : null;
    };

    return {
      t1: findDuration('Departed Plant'),
      t2a: findDuration('Arrived Site'),
      t2b: findDuration('Unloading / Pouring'),
      t3: findDuration('Returned'),
    };
  };

  const phaseBreakdown = getPhaseBreakdown();

  return (
    <div className="p-6 bg-slate-950 text-slate-100 min-h-screen space-y-6">
      {/* HEADER BAR */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-600/15 text-indigo-400 border border-indigo-500/30">
            <SquarePlay className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Timeline Replay &amp; Digital Twin
            </h1>
            <p className="text-xs text-slate-400">
              Dispatch Timeline Investigation &amp; Operational Journey Analysis
            </p>
          </div>
        </div>

        {/* Global Metadata & Live Status Header Ribbon */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-3 text-xs font-mono">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full border bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-semibold tracking-wide">SYNCHRONIZED</span>
            </div>
            <div className="hidden md:flex items-center space-x-1 text-slate-400 bg-slate-800/60 px-2.5 py-1 rounded border border-slate-700/50">
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              <span>v2.11-LIVE</span>
            </div>
            <div className="hidden sm:flex items-center space-x-1 text-slate-400 bg-slate-800/60 px-2.5 py-1 rounded border border-slate-700/50">
              <User className="w-3.5 h-3.5 text-indigo-400" />
              <span>Admin Operator</span>
            </div>
          </div>
        </div>
      </div>

      {/* GLOBAL DASHBOARD FILTER BAR */}
      <GlobalDashboardFilterBar />

      {/* TWO COLUMN WORKSPACE LAYOUT */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Replay Dispatch Queue (4 Cols) */}
        <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col h-[760px]">
          <div className="flex justify-between items-center pb-3 border-b border-slate-800 mb-3">
            <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              Replay Dispatch Queue ({totalCount})
            </h2>
            {selectedDispatchId && (
              <button
                onClick={() => setSelectedDispatchId(null)}
                className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold"
              >
                Clear
              </button>
            )}
          </div>

          {queueLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 space-y-2">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs">Loading queue from PostgreSQL...</span>
            </div>
          ) : queueError ? (
            <div className="flex-1 flex flex-col items-center justify-center text-rose-400 p-4 text-center">
              <AlertCircle className="w-6 h-6 mb-2" />
              <span className="text-xs font-semibold">{queueError}</span>
            </div>
          ) : dispatches.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-4 text-center">
              <FileText className="w-8 h-8 mb-2 text-slate-600" />
              <span className="text-xs">No dispatches match the selected scope filters.</span>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {dispatches.map((disp) => {
                const isSelected = disp.dispatch_id === selectedDispatchId;
                const isSyntheticFallbackTicket = disp.dispatch_number.startsWith('SYNTH-TCK-');

                return (
                  <button
                    key={disp.dispatch_id}
                    onClick={() => setSelectedDispatchId(disp.dispatch_id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      isSelected
                        ? 'bg-indigo-950/60 border-indigo-500 text-slate-100 ring-1 ring-indigo-500'
                        : 'bg-slate-800/50 hover:bg-slate-800 border-slate-700/60 text-slate-300'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-semibold text-sm text-slate-100 flex items-center gap-1.5">
                          {disp.dispatch_number}
                          {isSyntheticFallbackTicket && (
                            <span
                              className="text-[9px] font-mono px-1 py-0.2 bg-amber-950/80 text-amber-400 border border-amber-800/60 rounded"
                              title="ERP Ticket No. generated via fallback rules during import validation"
                            >
                              FALLBACK TICKET
                            </span>
                          )}
                        </span>
                      </div>
                      <span
                        className={
                          'text-[10px] font-bold px-1.5 py-0.5 rounded ' +
                          (disp.has_telemetry
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-slate-800 text-slate-400')
                        }
                      >
                        {disp.has_telemetry ? 'TELEMETRY' : 'ERP ONLY'}
                      </span>
                    </div>

                    <div className="text-xs text-slate-400 mt-1 flex justify-between">
                      <span>Status: {disp.status}</span>
                      <span>{formatDisplayDate(disp.dispatch_date)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Pagination Footer */}
          <div className="pt-3 border-t border-slate-800 flex justify-between items-center text-xs text-slate-400">
            <span>
              Page {page} of {Math.ceil(totalCount / pageSize) || 1}
            </span>
            <div className="space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 disabled:opacity-50"
              >
                Prev
              </button>
              <button
                disabled={page * pageSize >= totalCount}
                onClick={() => setPage((p) => p + 1)}
                className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Primary Dispatch Timeline Investigation Area (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col space-y-6">
          {!selectedDispatchId ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-16 text-center text-slate-400 flex flex-col items-center justify-center min-h-[400px]">
              <FileText className="w-12 h-12 text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-slate-200">
                No Dispatch Selected for Replay Investigation
              </h3>
              <p className="text-xs text-slate-500 max-w-md mt-1">
                Select a dispatch from the queue on the left to reconstruct its trip lifecycle, analyze phase duration breakdown, inspect telemetry metrics, and replay event milestones.
              </p>
            </div>
          ) : detailLoading ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-16 text-center text-slate-400 flex flex-col items-center justify-center min-h-[400px]">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className="text-sm font-medium">Loading authoritative dispatch timeline from PostgreSQL...</p>
            </div>
          ) : detailError ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-rose-400">
              <AlertCircle className="w-8 h-8 mx-auto mb-2" />
              <p className="font-semibold">{detailError}</p>
            </div>
          ) : detail ? (
            <>
              {/* 1. DISPATCH IDENTITY HEADER RIBBON WITH FRIENDLY NAMES & TOOLTIP UUIDs */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-md">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold text-slate-100 font-mono tracking-tight">
                        {detail.dispatch_number}
                      </h2>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                        {detail.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                      Operational Date:{' '}
                      <strong className="text-slate-200">
                        {formatOperationalDate(detail.lifecycle_events[0]?.timestamp || null)}
                      </strong>
                    </p>
                  </div>

                  {/* Correlated Alert Badge */}
                  {detail.correlated_alert_count > 0 && (
                    <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-semibold">
                      <AlertCircle className="w-4 h-4 text-rose-400" />
                      <span>{detail.correlated_alert_count} Correlated Alert(s)</span>
                    </div>
                  )}
                </div>

                {/* Friendly Entity Names Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 text-xs">
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <div className="flex items-center space-x-2 text-slate-400 mb-1">
                      <Building2 className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Plant</span>
                    </div>
                    <span className="font-semibold text-slate-200 text-xs truncate block">
                      {resolvePlantName(detail.plant_id)}
                    </span>
                    <span className="text-[9px] font-mono text-slate-500 block truncate">{detail.plant_id}</span>
                  </div>

                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <div className="flex items-center space-x-2 text-slate-400 mb-1">
                      <User className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Customer</span>
                    </div>
                    <span className="font-semibold text-slate-200 text-xs truncate block">
                      {resolveCustomerName(detail.customer_id)}
                    </span>
                    <span className="text-[9px] font-mono text-slate-500 block truncate">{detail.customer_id}</span>
                  </div>

                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <div className="flex items-center space-x-2 text-slate-400 mb-1">
                      <Truck className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Vehicle</span>
                    </div>
                    <span className="font-semibold text-slate-200 text-xs truncate block">
                      {detail.vehicle_id ? 'TM Unit (' + detail.vehicle_id.substring(0, 8) + ')' : 'N/A'}
                    </span>
                    <span className="text-[9px] font-mono text-slate-500 block truncate">{detail.vehicle_id || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* 2. DURATION ANALYSIS & TELEMETRY CARDS */}
              <div className={`grid grid-cols-1 ${detail.telemetry_summary.telemetry_matched ? 'md:grid-cols-2' : 'grid-cols-1'} gap-4`}>
                {/* Duration Summary with Prominent T1/T2a/T2b/T3 Breakdown */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="flex items-center text-slate-300 text-xs font-bold uppercase tracking-wider mb-2">
                    <Clock className="w-4 h-4 mr-1.5 text-indigo-400" />
                    Trip Duration Breakdown
                  </div>

                  <div className="flex items-baseline justify-between">
                    <div className="text-2xl font-bold text-slate-100 font-mono">
                      {detail.duration_summary.total_trip_duration_mins !== null
                        ? detail.duration_summary.total_trip_duration_mins.toFixed(1) + ' mins'
                        : 'Unavailable'}
                    </div>
                    <span
                      className={
                        'font-semibold px-2 py-0.5 rounded text-[10px] ' +
                        (detail.duration_summary.duration_completeness === 'COMPLETE'
                          ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/50'
                          : 'bg-amber-900/50 text-amber-300 border border-amber-700/50')
                      }
                    >
                      {detail.duration_summary.duration_completeness}
                    </span>
                  </div>

                  {/* Prominent Operational Phase Timings */}
                  <div className="mt-3 space-y-1.5 text-xs bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                    <div className="flex justify-between text-slate-300">
                      <span>T1 Transit:</span>
                      <span className="font-mono font-semibold">
                        {phaseBreakdown.t1 !== null ? phaseBreakdown.t1.toFixed(1) + ' mins' : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>T2a Holding:</span>
                      <span className="font-mono font-semibold">
                        {phaseBreakdown.t2a !== null ? phaseBreakdown.t2a.toFixed(1) + ' mins' : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>T2b Unloading:</span>
                      <span className="font-mono font-semibold">
                        {phaseBreakdown.t2b !== null ? phaseBreakdown.t2b.toFixed(1) + ' mins' : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>T3 Return:</span>
                      <span className="font-mono font-semibold">
                        {phaseBreakdown.t3 !== null ? phaseBreakdown.t3.toFixed(1) + ' mins' : 'N/A'}
                      </span>
                    </div>
                  </div>

                  {/* T2c SLA Retention Metric */}
                  {detail.t2c_retention_mins !== null && (
                    <div className="mt-3 pt-2 border-t border-slate-800 text-xs text-slate-400 flex justify-between items-center">
                      <span>T2c Excess Retention SLA:</span>
                      <span className="font-mono font-semibold text-amber-400">
                        {detail.t2c_retention_mins.toFixed(1)} mins
                      </span>
                    </div>
                  )}
                </div>

                {/* Telemetry Summary (Conditional: Only render when telemetry exists) */}
                {detail.telemetry_summary.telemetry_matched && (
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <div className="flex items-center text-slate-300 text-xs font-bold uppercase tracking-wider mb-2">
                      <Activity className="w-4 h-4 mr-1.5 text-emerald-400" />
                      Telemetry Analysis
                    </div>

                    <div className="space-y-1.5 text-xs bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                      <div className="flex justify-between text-slate-300">
                        <span>Avg Speed:</span>
                        <span className="font-mono font-semibold">
                          {detail.telemetry_summary.avg_speed_kmh?.toFixed(1) || 'N/A'} km/h
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span>Max Speed:</span>
                        <span className="font-mono font-semibold">
                          {detail.telemetry_summary.max_speed_kmh?.toFixed(1) || 'N/A'} km/h
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span>Drum Rotation:</span>
                        <span className="font-mono font-semibold">
                          {detail.telemetry_summary.drum_rotation_rpm?.toFixed(1) || 'N/A'} RPM
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 3. WS-08.5 SPATIAL CONTEXT & LOCATION CAPABILITY PANEL */}
              <TimelineSpatialContextPanel
                spatialContext={detail.spatial_context}
                plantName={resolvePlantName(detail.plant_id)}
                customerName={resolveCustomerName(detail.customer_id)}
              />

              {/* 4. AUTHORITATIVE LIFECYCLE JOURNEY (ALWAYS PERSISTENT) */}
              <DispatchLifecycleEventList
                events={detail.lifecycle_events}
                currentStepIndex={currentStepIndex}
              />

              {/* 5. SECONDARY REPLAY JOURNEY CONTROLS TOOLBAR */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
                <div className="mb-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Replay Journey Investigation Controls
                </div>
                <p className="text-[11px] text-slate-400 mb-3">
                  Replay the selected dispatch lifecycle timeline to inspect phase milestones across the trip journey.
                </p>

                <ReplayControlToolbar
                  isPlaying={isPlaying}
                  onPlayToggle={handlePlayToggle}
                  onReset={handleReset}
                  playbackSpeed={playbackSpeed}
                  onSpeedChange={setPlaybackSpeed}
                  currentStepIndex={currentStepIndex}
                  totalSteps={detail.lifecycle_events.length}
                  onStepChange={setCurrentStepIndex}
                  currentEventName={
                    detail.lifecycle_events[currentStepIndex]?.event_type || null
                  }
                />
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export const TimelineReplayDashboardPage: React.FC = () => {
  return (
    <DashboardSyncProvider onRefreshNeeded={async () => {}}>
      <DashboardFilterProvider>
        <TimelineReplayDashboardContent />
      </DashboardFilterProvider>
    </DashboardSyncProvider>
  );
};

export default TimelineReplayDashboardPage;
