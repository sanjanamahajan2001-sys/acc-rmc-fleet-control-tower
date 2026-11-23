import { formatDisplayDateTime } from '../../../../utils/date';
import { env } from '../../../../config/env';
/**
 * WS-07.7 Alert Center UI Workspace Content Widget
 * Production UI component for Operational Alert Center.
 * Reuses top shell & dataset context, renders alert KPI summary cards,
 * scope-aware filter bar, paginated data table, and detail/action drawer.
 * Enhanced for dispatcher legibility, human-readable metrics, and purpose-built operations.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Bell as LucideBell,
  CheckCircle2,
  AlertTriangle,
  Info,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X,
  UserCheck,
  ShieldCheck,
  AlertCircle,
  FileText,
  Activity,
  Layers,
  Clock,
  Database,
  Building,
  Users,
  Truck,
  ArrowUpRight,
  Check,
  Sparkles,
} from 'lucide-react';
import { useDashboardFilters } from '../../../site_dashboard/orchestration/DashboardFilterProvider';
import { useDashboardSync } from '../../../site_dashboard/orchestration/DashboardSyncProvider';
import {
  OperationalAlertSummary,
  OperationalAlertItem,
} from '../../types/operational_alerts_types';
import { IconAlertBell, IconCriticalAlert, IconCycleStopwatch, IconUserGroup, IconBatchingPlantFactory, IconDatasetDatabase, IconEfficiencyTimer } from '../../../../components/icons/LinealColorIcons';

/** Human-readable mapper for alert types */
const formatAlertType = (type: string): { label: string; icon: string; category: string } => {
  switch (type) {
    case 'PLANT_HOLDING_BOTTLENECK':
      return { label: 'Plant Loading Bottleneck', icon: '🏭', category: 'Plant Queue' };
    case 'SITE_RETENTION_EXCESSIVE':
      return { label: 'Excessive Site Unloading Delay', icon: '🚧', category: 'Site Detention' };
    case 'TRANSIT_DELAY_EXCESSIVE':
      return { label: 'Excessive Transit Delay', icon: '🚚', category: 'Transit Corridor' };
    case 'DEGRADED_DATA_QUALITY':
      return { label: 'Telemetry & Data Degradation', icon: '📡', category: 'Data Quality' };
    default:
      return {
        label: type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        icon: '⚠️',
        category: 'Exception',
      };
  }
};

/** Format metric names into friendly dispatcher labels */
const formatMetricName = (name: string): string => {
  switch (name) {
    case 't2a_holding_mins':
      return 'Plant Holding Time';
    case 't1_transit_mins':
      return 'Transit Travel Time';
    case 't3_unloading_mins':
    case 't3_site_retention_mins':
      return 'Site Retention Time';
    case 'total_cycle_mins':
      return 'Total Cycle Duration';
    default:
      return name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }
};

export const AlertCenterWorkspaceContent: React.FC = () => {
  const { filters, metadata } = useDashboardFilters();
  const { syncStatus } = useDashboardSync();
  const lastSyncTimestamp = syncStatus?.last_sync_timestamp;
  const activeDatasetId = filters.dataset_id || metadata?.dataset_id || undefined;

  // Primary API states
  const [summary, setSummary] = useState<OperationalAlertSummary | null>(null);
  const [alerts, setAlerts] = useState<OperationalAlertItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Widget-specific filter states
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('OPEN');
  const [alertTypeFilter, setAlertTypeFilter] = useState<string>('ALL');

  // Handler to trigger evaluation & generation of alerts for the active dataset
  const handleGenerateAlerts = async () => {
    setIsGenerating(true);
    setGenerateProgress('Evaluating business rules & generating alerts for active dataset...');
    setGenerateSuccess(null);
    try {
      const res = await fetch(`${env.VITE_API_BASE_URL}/alerts/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setGenerateSuccess(`Successfully evaluated ${data.dataset_id}: ${data.total_alerts} alerts active (${data.new_alerts_inserted} newly inserted).`);
      await fetchSummaryAndList();
    } catch (err: any) {
      alert('Alert Generation Failed: ' + (err.message || 'Unknown error'));
    } finally {
      setIsGenerating(false);
      setGenerateProgress(null);
    }
  };

  // Detail drawer state
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [detailAlert, setDetailAlert] = useState<OperationalAlertItem | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);

  // Action form state
  const [ackNotes, setAckNotes] = useState<string>('');
  const [operatorName, setOperatorName] = useState<string>('Operator_ControlTower');
  const [resolveReason, setResolveReason] = useState<string>('Operational Queue Cleared');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);

  // General loading & error
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Active dataset alert evaluation state
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generateProgress, setGenerateProgress] = useState<string | null>(null);
  const [generateSuccess, setGenerateSuccess] = useState<string | null>(null);

  // Master fetch summary & alerts callback (memoized)
  const fetchSummaryAndList = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      // Build query params propagating Global Filters & Local Alert Filters
      const queryParams = new URLSearchParams();
      if (filters.plant_id && filters.plant_id !== 'ALL') queryParams.set('plant_id', filters.plant_id);
      if (filters.customer_id && filters.customer_id !== 'ALL') queryParams.set('customer_id', filters.customer_id);
      if (activeDatasetId) queryParams.set('dataset_id', activeDatasetId);

      if (severityFilter !== 'ALL') queryParams.set('severity', severityFilter);
      if (statusFilter !== 'ALL') queryParams.set('status', statusFilter);
      if (alertTypeFilter !== 'ALL') queryParams.set('alert_type', alertTypeFilter);

      queryParams.set('page', page.toString());
      queryParams.set('page_size', pageSize.toString());

      // 1. Fetch Summary
      const summaryRes = await fetch(`${env.VITE_API_BASE_URL}/alerts/summary?${queryParams.toString()}`);
      if (!summaryRes.ok) {
        throw new Error(`Summary API error: HTTP ${summaryRes.status}`);
      }
      const summaryData: OperationalAlertSummary = await summaryRes.json();
      setSummary(summaryData);

      // 2. Fetch Paginated List
      const listRes = await fetch(`${env.VITE_API_BASE_URL}/alerts?${queryParams.toString()}`);
      if (!listRes.ok) {
        throw new Error('Alerts List API error: HTTP ' + listRes.status);
      }
      const listData = await listRes.json();
      setAlerts(listData.items || []);
      setTotalCount(listData.total_count || 0);
      setTotalPages(listData.total_pages || 1);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to fetch alert workspace data');
    } finally {
      setIsLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, activeDatasetId, severityFilter, statusFilter, alertTypeFilter, page, pageSize]);

  // Fetch summary & alerts list when filters or sync state changes
  useEffect(() => {
    fetchSummaryAndList();
  }, [fetchSummaryAndList, lastSyncTimestamp]);

  // Fetch detail alert when drawer opens (preserves action notifications if called from refresh)
  const fetchDetailAlert = useCallback(async (alertId: string, clearNotifications: boolean = true) => {
    setIsDetailLoading(true);
    if (clearNotifications) {
      setActionError(null);
      setActionSuccess(null);
    }
    try {
      const queryParams = new URLSearchParams();
      if (filters.plant_id && filters.plant_id !== 'ALL') queryParams.set('plant_id', filters.plant_id);
      if (filters.customer_id && filters.customer_id !== 'ALL') queryParams.set('customer_id', filters.customer_id);

      const res = await fetch(env.VITE_API_BASE_URL + '/alerts/' + alertId + '?' + queryParams.toString());
      if (!res.ok) {
        if (res.status === 404) throw new Error('Alert not found or inaccessible under active scope.');
        throw new Error('Detail API error: HTTP ' + res.status);
      }
      const data = await res.json();
      setDetailAlert(data);
    } catch (err: any) {
      setActionError(err.message || 'Failed to load alert detail.');
      setDetailAlert(null);
    } finally {
      setIsDetailLoading(false);
    }
  }, [filters.plant_id, filters.customer_id]);

  // Close drawer or re-fetch when selectedAlertId changes
  useEffect(() => {
    if (!selectedAlertId) {
      setDetailAlert(null);
      return;
    }
    fetchDetailAlert(selectedAlertId, true);
  }, [selectedAlertId, fetchDetailAlert]);

  // Scope Isolation Guard: Close drawer if active global scope changes while drawer is open
  useEffect(() => {
    if (selectedAlertId) {
      setSelectedAlertId(null);
      setDetailAlert(null);
    }
  }, [filters.plant_id, filters.customer_id]);

  // Coordinated Post-Action Refresh Mechanism
  const refreshAlertWorkspace = useCallback(async (alertId?: string) => {
    await fetchSummaryAndList();
    if (alertId) {
      await fetchDetailAlert(alertId, false);
    }
  }, [fetchSummaryAndList, fetchDetailAlert]);

  // Acknowledge Action Handler
  const handleAcknowledge = async () => {
    if (!selectedAlertId || isActionLoading) return;
    setIsActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await fetch(env.VITE_API_BASE_URL + '/alerts/' + selectedAlertId + '/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledged_by: operatorName, notes: ackNotes }),
      });

      if (res.status === 409) {
        setActionError('409 CONFLICT: Alert state has been modified concurrently. Refreshing state...');
        await refreshAlertWorkspace(selectedAlertId);
        return;
      }

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Failed to acknowledge alert.');
      }

      setActionSuccess('Alert successfully ACKNOWLEDGED.');
      setAckNotes('');
      // Await complete authoritative refresh of detail, summary, and list
      await refreshAlertWorkspace(selectedAlertId);
    } catch (err: any) {
      setActionError(err.message || 'Acknowledge operation failed.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Resolve Action Handler
  const handleResolve = async () => {
    if (!selectedAlertId || isActionLoading) return;
    setIsActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await fetch(env.VITE_API_BASE_URL + '/alerts/' + selectedAlertId + '/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved_by: operatorName, resolution_reason: resolveReason }),
      });

      if (res.status === 409) {
        setActionError('409 CONFLICT: Alert state has been modified concurrently. Refreshing state...');
        await refreshAlertWorkspace(selectedAlertId);
        return;
      }

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Failed to resolve alert.');
      }

      setActionSuccess('Alert successfully RESOLVED.');
      // Await complete authoritative refresh of detail, summary, and list
      await refreshAlertWorkspace(selectedAlertId);
    } catch (err: any) {
      setActionError(err.message || 'Resolve operation failed.');
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="alert-center-workspace">
      {/* Alert KPI Summary Strip (Primary KPI Row) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="alert-summary-strip">
        {/* Total Active */}
        <div
          onClick={() => { setStatusFilter('ALL'); setPage(1); }}
          className="p-4 rounded-lg border border-slate-200/90 bg-white flex flex-col justify-between shadow-xs transition cursor-pointer hover:border-slate-400"
        >
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Total Active</span>
            <div className="shrink-0 flex items-center justify-center">
              <IconAlertBell className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-slate-900">
              {summary?.total_active_alerts ?? 0}
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
              Active Exceptions
            </span>
          </div>
        </div>

        {/* Critical */}
        <div
          onClick={() => { setSeverityFilter('CRITICAL'); setStatusFilter('OPEN'); setPage(1); }}
          className="p-4 rounded-lg border border-rose-300 bg-rose-50/70 flex flex-col justify-between shadow-xs transition cursor-pointer hover:border-rose-400"
        >
          <div className="flex items-center justify-between text-rose-800">
            <span className="text-[11px] font-bold uppercase tracking-wider">Critical</span>
            <div className="shrink-0 flex items-center justify-center">
              <IconCriticalAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-rose-900">
              {summary?.critical_count ?? 0}
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-rose-100 text-rose-800 border border-rose-200">
              P1 Immediate
            </span>
          </div>
        </div>

        {/* Warning */}
        <div
          onClick={() => { setSeverityFilter('WARNING'); setStatusFilter('OPEN'); setPage(1); }}
          className="p-4 rounded-lg border border-amber-300 bg-amber-50/70 flex flex-col justify-between shadow-xs transition cursor-pointer hover:border-amber-400"
        >
          <div className="flex items-center justify-between text-amber-800">
            <span className="text-[11px] font-bold uppercase tracking-wider">Warning</span>
            <div className="shrink-0 flex items-center justify-center">
              <IconCriticalAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-amber-900">
              {summary?.warning_count ?? 0}
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-800 border border-amber-200">
              P2 SLA Risk
            </span>
          </div>
        </div>

        {/* Info */}
        <div
          onClick={() => { setSeverityFilter('INFO'); setPage(1); }}
          className="p-4 rounded-lg border border-blue-200 bg-blue-50/70 flex flex-col justify-between shadow-xs transition cursor-pointer hover:border-blue-400"
        >
          <div className="flex items-center justify-between text-blue-800">
            <span className="text-[11px] font-bold uppercase tracking-wider">Info</span>
            <div className="shrink-0 flex items-center justify-center">
              <IconEfficiencyTimer className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-blue-900">
              {summary?.info_count ?? 0}
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-blue-100 text-blue-800 border border-blue-200">
              P3 Info
            </span>
          </div>
        </div>

        {/* Acknowledged / In Triage */}
        <div
          onClick={() => { setStatusFilter('ACKNOWLEDGED'); setPage(1); }}
          className="p-4 rounded-lg border border-blue-200 bg-blue-50/70 flex flex-col justify-between col-span-2 md:col-span-1 shadow-xs transition cursor-pointer hover:border-blue-400"
        >
          <div className="flex items-center justify-between text-blue-800">
            <span className="text-[11px] font-bold uppercase tracking-wider">Acknowledged</span>
            <div className="shrink-0 flex items-center justify-center">
              <IconUserGroup className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-blue-900" data-testid="summary-ack-count">
              {summary?.acknowledged_count ?? 0}
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-blue-100 text-blue-800 border border-blue-200">
              In Triage
            </span>
          </div>
        </div>
      </div>

      {/* Alert Filter Control Bar */}
      <div
        className="p-3.5 rounded-lg border border-slate-200/90 bg-white flex flex-wrap items-center justify-between gap-4 shadow-xs"
        data-testid="alert-filter-controls"
      >
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-900">
            <Filter className="w-3.5 h-3.5 text-blue-700" />
            <span>Operational Filters:</span>
          </div>

          {/* Severity Dropdown */}
          <div className="flex items-center space-x-1">
            <span className="text-[11px] text-slate-500 font-medium">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
              className="text-xs px-2.5 py-1 rounded-md border border-slate-200 font-semibold focus:outline-none bg-white text-slate-900"
              data-testid="severity-filter-select"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">🔴 Critical (P1)</option>
              <option value="WARNING">🟡 Warning (P2)</option>
              <option value="INFO">🔵 Info (P3)</option>
            </select>
          </div>

          {/* Status Dropdown */}
          <div className="flex items-center space-x-1">
            <span className="text-[11px] text-slate-500 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="text-xs px-2.5 py-1 rounded-md border border-slate-200 font-semibold focus:outline-none bg-white text-slate-900"
              data-testid="status-filter-select"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN">Open (Requires Action)</option>
              <option value="ACKNOWLEDGED">Acknowledged (In Triage)</option>
              <option value="RESOLVED">Resolved</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>

          {/* Alert Type Dropdown */}
          <div className="flex items-center space-x-1">
            <span className="text-[11px] text-slate-500 font-medium">Exception Type:</span>
            <select
              value={alertTypeFilter}
              onChange={(e) => { setAlertTypeFilter(e.target.value); setPage(1); }}
              className="text-xs px-2.5 py-1 rounded-md border border-slate-200 font-semibold focus:outline-none bg-white text-slate-900"
              data-testid="alert-type-filter-select"
            >
              <option value="ALL">All Exception Types</option>
              <option value="PLANT_HOLDING_BOTTLENECK">Plant Loading Bottleneck</option>
              <option value="SITE_RETENTION_EXCESSIVE">Excessive Site Unloading Delay</option>
              <option value="TRANSIT_DELAY_EXCESSIVE">Excessive Transit Delay</option>
              <option value="DEGRADED_DATA_QUALITY">Telemetry &amp; Data Degradation</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs font-medium text-slate-500 font-mono">
          <span className="bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
            Showing <strong className="text-slate-900 tabular-nums">{totalCount}</strong> matching alerts
          </span>
          <button
            onClick={handleGenerateAlerts}
            disabled={isGenerating || isLoading}
            className="p-1.5 px-3 rounded-md bg-blue-700 hover:bg-blue-800 text-white transition flex items-center gap-1.5 font-bold text-xs shadow-xs cursor-pointer disabled:opacity-50"
            title="Re-evaluate all business rules and generate alerts for the active dataset"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>{isGenerating ? 'Evaluating Alerts...' : 'Re-evaluate Active Alerts'}</span>
          </button>
          <button
            onClick={() => fetchSummaryAndList()}
            className="p-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 transition flex items-center gap-1 font-bold text-xs text-slate-700 shadow-xs cursor-pointer"
            title="Refresh Alert Stream"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Generation Progress Indicator Banner */}
      {generateProgress && (
        <div className="p-3.5 rounded-lg border border-emerald-300 bg-emerald-50 text-xs flex items-center space-x-2.5 font-bold text-emerald-800 animate-pulse shadow-xs">
          <RefreshCw className="w-4 h-4 animate-spin text-emerald-700 shrink-0" />
          <span>{generateProgress}</span>
        </div>
      )}
      {generateSuccess && !generateProgress && (
        <div className="p-3.5 rounded-lg border border-emerald-300 bg-emerald-50 text-xs flex items-center justify-between font-bold text-emerald-800 shadow-xs">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{generateSuccess}</span>
          </div>
          <button onClick={() => setGenerateSuccess(null)} className="text-emerald-700 hover:text-emerald-900 cursor-pointer text-xs">
            ✕
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div
          className="p-12 rounded-lg border border-slate-200/90 bg-white animate-pulse flex items-center justify-center space-x-3 text-xs font-bold text-slate-500"
          data-testid="alert-loading-state"
        >
          <RefreshCw className="w-5 h-5 animate-spin text-blue-700" />
          <span>Refreshing operational alert stream...</span>
        </div>
      )}

      {/* Error State */}
      {fetchError && !isLoading && (
        <div
          className="p-4 rounded-lg border border-rose-300 bg-rose-50 text-xs flex items-center justify-between font-bold text-rose-800"
          data-testid="alert-error-state"
        >
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-700" />
            <span>{fetchError}</span>
          </div>
          <button
            onClick={() => fetchSummaryAndList()}
            className="px-3 py-1 rounded-md font-bold text-xs border border-rose-300 bg-white text-rose-700 hover:bg-rose-50 cursor-pointer shadow-xs"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !fetchError && alerts.length === 0 && (
        <div
          className="p-12 rounded-lg border border-slate-200/90 bg-white text-center space-y-3 shadow-xs"
          data-testid="alert-empty-state"
        >
          <div className="w-12 h-12 mx-auto rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center">
            <ShieldCheck className="w-6 h-6 text-emerald-700" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">
            No Active Operational Exceptions
          </h3>
          <p className="text-xs font-normal max-w-md mx-auto text-slate-500">
            All batch cycles, turnaround metrics, and transit times are operating within SLA tolerances for the selected plant and customer parameters.
          </p>
        </div>
      )}

      {/* Operational Alert List Table */}
      {!isLoading && !fetchError && alerts.length > 0 && (
        <div
          className="rounded-lg border border-slate-200/90 bg-white overflow-hidden shadow-xs"
          data-testid="alert-list-table"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 uppercase font-mono font-bold tracking-wider text-[11px] text-slate-600">
                <tr>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Operational Exception</th>
                  <th className="px-4 py-3">Scope / Plant</th>
                  <th className="px-4 py-3">SLA Metric Variance</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Detected At</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-900">
                {alerts.map((item) => {
                  const typeMeta = formatAlertType(item.alert_type);
                  const variance = (item.actual_value - item.threshold_value);
                  const isPositiveVariance = variance > 0;

                  return (
                    <tr key={item.id} className="hover:bg-slate-50 transition">
                      {/* Severity Badge */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                            item.severity === 'CRITICAL'
                              ? 'bg-rose-50 border-rose-300 text-rose-800'
                              : item.severity === 'WARNING'
                              ? 'bg-amber-50 border-amber-300 text-amber-800'
                              : 'bg-blue-50 border-blue-200 text-blue-800'
                          }`}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-current" />
                          {item.severity}
                        </span>
                      </td>

                      {/* Exception Type */}
                      <td className="px-4 py-3">
                        <div className="font-bold text-slate-900 flex items-center gap-1.5">
                          <span>{typeMeta.label}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5 flex items-center gap-2">
                          <span className="bg-slate-100 px-1 rounded text-slate-600 font-sans border border-slate-200">{typeMeta.category}</span>
                          {item.dispatch_id && (
                            <span className="text-blue-700 font-medium font-mono">Ref: {item.dispatch_id}</span>
                          )}
                        </div>
                      </td>

                      {/* Scope / Plant */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="font-bold text-slate-800 flex items-center gap-1">
                          <Building className="w-3.5 h-3.5 text-slate-400" />
                          <span>{item.plant_id ? item.plant_id.replace('ACC_', '') : 'Global'}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 truncate max-w-[140px]" title={item.customer_id || 'All Customers'}>
                          {item.customer_id || 'All Customers'}
                        </div>
                      </td>

                      {/* SLA Metric Variance */}
                      <td className="px-4 py-3 font-mono">
                        <div className="flex items-center gap-1.5 font-bold text-slate-900">
                          <span className="font-sans font-medium text-slate-600">{formatMetricName(item.metric_name)}:</span>
                          <span className="tabular-nums text-amber-800">{item.actual_value} {item.unit}</span>
                          {isPositiveVariance && (
                            <span className="text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-200 px-1 rounded-md tabular-nums">
                              (+{variance.toFixed(0)}{item.unit})
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          Threshold: <span className="font-bold tabular-nums">{item.threshold_value} {item.unit}</span>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                            item.status === 'OPEN'
                              ? 'bg-rose-50 border-rose-300 text-rose-800'
                              : item.status === 'ACKNOWLEDGED'
                              ? 'bg-blue-50 border-blue-200 text-blue-800'
                              : 'bg-emerald-50 border-emerald-300 text-emerald-800'
                          }`}
                        >
                          {item.status === 'OPEN' ? 'Requires Action' : item.status === 'ACKNOWLEDGED' ? 'In Triage' : 'Resolved'}
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-slate-500 tabular-nums">
                        {new Date(item.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>

                      {/* Action Button */}
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <button
                          onClick={() => setSelectedAlertId(item.id)}
                          className="px-3 py-1.5 rounded-md border border-slate-200 bg-white font-bold text-xs text-slate-800 hover:bg-slate-50 hover:text-blue-700 transition shadow-xs cursor-pointer"
                          data-testid={'inspect-alert-btn-' + item.id}
                        >
                          Inspect &amp; Resolve
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div
            className="p-3.5 border-t border-slate-100 flex items-center justify-between text-xs font-mono text-slate-500"
            data-testid="alert-pagination-bar"
          >
            <span>
              Showing Page <strong className="font-bold text-slate-900 tabular-nums">{page}</strong> of <strong className="font-bold text-slate-900 tabular-nums">{totalPages}</strong> (<span className="tabular-nums">{totalCount}</span> total alerts)
            </span>
            <div className="flex items-center space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2.5 py-1 rounded-md border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50 font-bold text-slate-700 flex items-center gap-1 shadow-xs cursor-pointer"
                data-testid="pagination-prev-btn"
              >
                <ChevronLeft size={14} />
                <span>Prev</span>
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-2.5 py-1 rounded-md border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50 font-bold text-slate-700 flex items-center gap-1 shadow-xs cursor-pointer"
                data-testid="pagination-next-btn"
              >
                <span>Next</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alert Detail & Lifecycle Action Drawer */}
      {selectedAlertId && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex justify-end" data-testid="alert-detail-drawer">
          <div
            className="w-full max-w-lg border-l h-full p-6 overflow-y-auto space-y-6 flex flex-col justify-between shadow-2xl"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            <div className="space-y-6">
              {/* Drawer Header */}
              <div className="flex items-center justify-between pb-4 border-b" style={{ borderColor: '#DCE2EA' }}>
                <div>
                  <h3 className="text-lg font-bold flex items-center gap-2" style={{ color: '#172033' }} data-testid="drawer-title">
                    <IconAlertBell className="w-5 h-5" /> Operational Alert Details
                  </h3>
                  <p className="text-xs font-mono text-slate-500 mt-0.5" data-testid="drawer-alert-id">
                    ID: {selectedAlertId}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedAlertId(null)}
                  className="p-1.5 rounded-lg border hover:bg-slate-100 text-slate-600"
                  style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
                  data-testid="close-drawer-btn"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Action Error / Success Notifications */}
              {actionError && (
                <div
                  className="p-3 border border-rose-300 rounded-md text-xs font-bold bg-rose-50 text-rose-800"
                  data-testid="drawer-action-error"
                >
                  {actionError}
                </div>
              )}
              {actionSuccess && (
                <div
                  className="p-3 border border-emerald-300 rounded-md text-xs font-bold bg-emerald-50 text-emerald-800"
                  data-testid="drawer-action-success"
                >
                  {actionSuccess}
                </div>
              )}

              {/* Drawer Loading State */}
              {isDetailLoading && (
                <div className="p-8 text-center flex items-center justify-center space-x-2 text-xs font-bold text-slate-500" data-testid="drawer-loading-state">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-700" />
                  <span>Loading alert evidence payload...</span>
                </div>
              )}

              {detailAlert && !isDetailLoading && (
                <div className="space-y-5 text-xs text-slate-800" data-testid="drawer-alert-detail-content">
                  {/* Alert Core Info Grid */}
                  <div className="p-4 rounded-md border space-y-2.5 bg-slate-50 border-slate-200/80">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-amber-600" /> Exception Type
                      </span>
                      <span className="font-bold text-amber-900" data-testid="drawer-alert-type">
                        {formatAlertType(detailAlert.alert_type).label}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5" /> Severity Tier
                      </span>
                      <span className="font-bold text-slate-900" data-testid="drawer-severity">
                        {detailAlert.severity}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-blue-700" /> Lifecycle Status
                      </span>
                      <span className="font-bold text-blue-700 font-mono" data-testid="drawer-status">
                        {detailAlert.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <Building className="w-3.5 h-3.5" /> Plant Origin
                      </span>
                      <span className="font-bold text-slate-900 font-mono" data-testid="drawer-plant-id">
                        {detailAlert.plant_id || 'Global Scope'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5" /> Customer Scope
                      </span>
                      <span className="font-bold text-slate-900" data-testid="drawer-customer-id">
                        {detailAlert.customer_id || 'All Customers'}
                      </span>
                    </div>
                    {detailAlert.dispatch_id && (
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-blue-700" /> Dispatch Reference
                        </span>
                        <span className="font-mono text-[11px] font-bold text-blue-700" data-testid="drawer-dispatch-id">
                          {detailAlert.dispatch_id}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" /> Detected Timestamp
                      </span>
                      <span className="font-mono text-slate-600" data-testid="drawer-detected-at">
                        {formatDisplayDateTime(detailAlert.detected_at, true)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-500 flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5" /> Rule Engine Version
                      </span>
                      <span className="font-mono text-slate-600">{detailAlert.rule_version}</span>
                    </div>
                  </div>

                  {/* Observed Metric & Threshold Variance Card */}
                  <div
                    className="p-4 rounded-md border border-amber-300 bg-amber-50/70 space-y-2 shadow-2xs"
                    data-testid="drawer-metric-variance-card"
                  >
                    <h4 className="font-bold flex items-center gap-1.5 text-amber-900 text-xs uppercase tracking-wider">
                      <Activity className="w-4 h-4 text-amber-700" /> Observed SLA Metric Variance
                    </h4>
                    <div className="grid grid-cols-3 gap-2 text-center pt-1 font-mono">
                      <div className="p-2.5 rounded-md border bg-white border-amber-200">
                        <div className="text-[10px] text-slate-500 font-medium font-sans">Observed Metric</div>
                        <div className="text-sm font-bold text-amber-800 mt-0.5 tabular-nums" data-testid="drawer-actual-value">
                          {detailAlert.actual_value} <span className="text-[10px] font-normal font-sans">{detailAlert.unit}</span>
                        </div>
                      </div>
                      <div className="p-2.5 rounded-md border bg-white border-amber-200">
                        <div className="text-[10px] text-slate-500 font-medium font-sans">SLA Threshold</div>
                        <div className="text-sm font-bold text-slate-800 mt-0.5 tabular-nums" data-testid="drawer-threshold-value">
                          {detailAlert.threshold_value} <span className="text-[10px] font-normal font-sans">{detailAlert.unit}</span>
                        </div>
                      </div>
                      <div className="p-2.5 rounded-md border bg-white border-amber-200">
                        <div className="text-[10px] text-slate-500 font-medium font-sans">Overrun Variance</div>
                        <div className="text-sm font-bold text-rose-700 mt-0.5 tabular-nums" data-testid="drawer-variance-value">
                          +{(detailAlert.actual_value - detailAlert.threshold_value).toFixed(1)} <span className="text-[10px] font-normal font-sans">{detailAlert.unit}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Business Impact & Mitigation Action */}
                  <div className="space-y-3">
                    <div>
                      <h4 className="font-bold mb-1.5 flex items-center gap-1.5 text-slate-900 text-xs uppercase tracking-wider">
                        <Activity className="w-3.5 h-3.5 text-rose-700" /> Business &amp; Operational Impact
                      </h4>
                      <p
                        className="p-3 rounded-md border font-medium text-slate-700 leading-relaxed bg-slate-50 border-slate-200/80"
                        data-testid="drawer-business-impact"
                      >
                        {detailAlert.business_impact}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-bold mb-1.5 flex items-center gap-1.5 text-slate-900 text-xs uppercase tracking-wider">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" /> Recommended Mitigation Directive
                      </h4>
                      <p
                        className="p-3 rounded-md border font-medium text-slate-700 leading-relaxed bg-slate-50 border-slate-200/80"
                        data-testid="drawer-recommended-action"
                      >
                        {detailAlert.recommended_action}
                      </p>
                    </div>
                  </div>

                  {/* Evidence Payload */}
                  <div data-testid="drawer-evidence-section">
                    <h4 className="font-bold mb-1.5 flex items-center gap-1.5 text-slate-900 text-xs uppercase tracking-wider">
                      <FileText className="w-3.5 h-3.5 text-blue-700" /> Forensic Evidence Payload
                    </h4>
                    {detailAlert.evidence_json && Object.keys(detailAlert.evidence_json).length > 0 ? (
                      <pre
                        className="p-3 rounded-md border font-mono text-[11px] overflow-x-auto bg-slate-50 border-slate-200 text-slate-800"
                        data-testid="drawer-evidence-json"
                      >
                        {JSON.stringify(detailAlert.evidence_json, null, 2)}
                      </pre>
                    ) : (
                      <div
                        className="p-3 rounded-md border italic text-[11px] bg-slate-50 border-slate-200 text-slate-500"
                        data-testid="drawer-no-evidence-banner"
                      >
                        No additional forensic evidence attached
                      </div>
                    )}
                  </div>

                  {/* Audit Trail */}
                  {(detailAlert.acknowledged_by || detailAlert.resolved_by) && (
                    <div
                      className="p-3.5 rounded-md border space-y-1 font-mono text-[11px] bg-slate-50 border-slate-200"
                      data-testid="drawer-audit-log"
                    >
                      <h4 className="font-sans font-bold mb-1 text-slate-900 text-xs uppercase tracking-wider">Dispatcher Audit Trail</h4>
                      {detailAlert.acknowledged_by && (
                        <div className="font-semibold text-blue-700">
                          ACK: {detailAlert.acknowledged_by} @ {detailAlert.acknowledged_at ? new Date(detailAlert.acknowledged_at).toLocaleString() : ''}
                        </div>
                      )}
                      {detailAlert.resolved_by && (
                        <div className="font-semibold text-emerald-700">
                          RES: {detailAlert.resolved_by} ({detailAlert.resolution_reason}) @ {detailAlert.resolved_at ? new Date(detailAlert.resolved_at).toLocaleString() : ''}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Operator Action Panel */}
                  <div
                    className="p-4 rounded-md border space-y-4 pt-4 shadow-xs bg-white border-slate-200"
                    data-testid="drawer-lifecycle-panel"
                  >
                    <h4 className="font-bold flex items-center gap-1.5 text-slate-900 text-xs uppercase tracking-wider">
                      <ShieldCheck className="w-4 h-4 text-blue-700" /> Operator Triage &amp; Resolution Panel
                    </h4>

                    {/* Operator Signature Input */}
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-500">Operator Digital Signature</label>
                      <input
                        type="text"
                        value={operatorName}
                        onChange={(e) => setOperatorName(e.target.value)}
                        className="w-full border rounded-md px-3 py-1.5 text-xs font-semibold focus:outline-none bg-white border-slate-200 text-slate-900 font-mono"
                        data-testid="operator-signature-input"
                      />
                    </div>

                    {/* Acknowledge Action Form */}
                    {detailAlert.status === 'OPEN' && (
                      <div className="space-y-2 pt-2 border-t border-slate-100">
                        <label className="text-[11px] font-semibold text-slate-500">Triage Notes (Optional)</label>
                        <input
                          type="text"
                          placeholder="e.g. Dispatched yard marshal to expedite truck loading..."
                          value={ackNotes}
                          onChange={(e) => setAckNotes(e.target.value)}
                          className="w-full border rounded-md px-3 py-1.5 text-xs font-medium focus:outline-none bg-white border-slate-200 text-slate-900"
                          data-testid="ack-notes-input"
                        />
                        <button
                          onClick={handleAcknowledge}
                          disabled={isActionLoading}
                          className="w-full py-2 rounded-md text-white font-bold text-xs transition disabled:opacity-50 flex items-center justify-center space-x-2 bg-blue-700 hover:bg-blue-800 shadow-xs cursor-pointer"
                          data-testid="ack-alert-btn"
                        >
                          {isActionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                          <span>Acknowledge Exception (Move to Triage)</span>
                        </button>
                      </div>
                    )}

                    {/* Resolve Action Form */}
                    {(detailAlert.status === 'OPEN' || detailAlert.status === 'ACKNOWLEDGED') && (
                      <div className="space-y-2 pt-2 border-t border-slate-100">
                        <label className="text-[11px] font-semibold text-slate-500">Resolution Reason</label>
                        <select
                          value={resolveReason}
                          onChange={(e) => setResolveReason(e.target.value)}
                          className="w-full border rounded-md px-3 py-1.5 text-xs font-semibold focus:outline-none bg-white border-slate-200 text-slate-900"
                          data-testid="resolve-reason-select"
                        >
                          <option value="Operational Queue Cleared">Operational Queue Cleared</option>
                          <option value="Customer Site SLA Met">Customer Site SLA Met</option>
                          <option value="Speed Normalised">Transit Speed Normalised</option>
                          <option value="Manual Override Approved">Manual Dispatch Override Approved</option>
                        </select>
                        <button
                          onClick={handleResolve}
                          disabled={isActionLoading}
                          className="w-full py-2 rounded-md text-white font-bold text-xs transition disabled:opacity-50 flex items-center justify-center space-x-2 bg-emerald-700 hover:bg-emerald-800 shadow-xs cursor-pointer"
                          data-testid="resolve-alert-btn"
                        >
                          {isActionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                          <span>Resolve &amp; Close Exception</span>
                        </button>
                      </div>
                    )}

                    {detailAlert.status === 'RESOLVED' && (
                      <div className="p-3 border rounded-md text-center text-xs font-bold bg-emerald-50 border-emerald-300 text-emerald-800">
                        ✓ Alert is RESOLVED and closed. No further triage actions required.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-200 text-center">
              <button
                onClick={() => setSelectedAlertId(null)}
                className="px-5 py-2 rounded-md border font-bold text-xs transition hover:bg-slate-50 bg-white border-slate-200 text-slate-700 shadow-xs cursor-pointer"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AlertCenterWorkspaceContent;
