import { usePermissions } from '../../../hooks/usePermissions';
import React, { useEffect, useState, useCallback } from 'react';
import { ShieldAlert, CheckCircle2, RefreshCw, Filter, Info } from 'lucide-react';
import { IconSupervisorDirectives } from '../../../components/icons/LinealColorIcons';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { DashboardFilterProvider, useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { actionExecutionApi, ActionLogItem } from '../api/actionExecutionApi';
import { ActionSummaryKPIRibbon } from '../components/ActionSummaryKPIRibbon';
import { ControlTowerActionCard } from '../components/ControlTowerActionCard';
import {
  AcceptActionModal,
  ConfirmExecutionModal,
  RejectDeferModal,
  ActionAuditModal,
} from '../components/ActionModals';

const safeUUID = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
};

export const ControlTowerActionsContent: React.FC = () => {
  const { filters } = useDashboardFilters();
  const [actions, setActions] = useState<ActionLogItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modal States
  const [selectedAction, setSelectedAction] = useState<ActionLogItem | null>(null);
  const [isAcceptOpen, setIsAcceptOpen] = useState(false);
  const [isConfirmExecOpen, setIsConfirmExecOpen] = useState(false);
  const [isRejectDeferOpen, setIsRejectDeferOpen] = useState(false);
  const [rejectDeferMode, setRejectDeferMode] = useState<'REJECT' | 'DEFER'>('REJECT');
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Status & Pagination Filter
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [pageSize, setPageSize] = useState<number>(20);
  const [currentPage, setCurrentPage] = useState<number>(1);

  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const { canEdit } = usePermissions();
  const canExecuteActions = canEdit('control_tower_actions');
  const [generateProgress, setGenerateProgress] = useState<string | null>(null);

  const handleGenerateActions = async () => {
    setIsGenerating(true);
    setGenerateProgress('Evaluating SLA breaches, ML predictions & generating recommendations...');
    try {
      await actionExecutionApi.generateActions();
      setGenerateProgress('Syncing action queue...');
      await fetchActionQueue();
    } catch (err: any) {
      alert('Generation Failed: ' + err.message);
    } finally {
      setIsGenerating(false);
      setGenerateProgress(null);
    }
  };

  const fetchActionQueue = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await actionExecutionApi.getActionQueue({
        plant_id: filters.plant_id,
        customer_id: filters.customer_id,
        dataset_type: filters.dataset_type,
        action_status: statusFilter === 'ALL' ? undefined : statusFilter,
      });
      setActions(res.items || []);
      setCurrentPage(1);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch action queue recommendations');
    } finally {
      setIsLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, statusFilter]);

  useEffect(() => {
    fetchActionQueue();
  }, [fetchActionQueue]);

  // Action Handlers
  const handleOpenAccept = (action: ActionLogItem) => {
    setSelectedAction(action);
    setIsAcceptOpen(true);
  };

  const handleConfirmAccept = async (notes: string, role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN') => {
    if (!selectedAction) return;
    setIsSubmitting(true);
    try {
      await actionExecutionApi.acceptRecommendation(selectedAction.action_id, {
        dispatcher_id: 'USER-DISPATCHER-1',
        dispatcher_role: role,
        idempotency_key: 'EXEC-ACCEPT-' + safeUUID(),
        version_lock: selectedAction.version_lock,
        notes,
      });
      setIsAcceptOpen(false);
      await fetchActionQueue();
    } catch (err: any) {
      alert('Accept Failure: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartProgress = async (action: ActionLogItem) => {
    setIsLoading(true);
    try {
      await actionExecutionApi.startProgress(action.action_id, {
        dispatcher_id: 'USER-DISPATCHER-1',
        dispatcher_role: 'DISPATCHER',
        idempotency_key: 'EXEC-START-' + safeUUID(),
        version_lock: action.version_lock,
        notes: 'Operational progress started by dispatcher',
      });
      await fetchActionQueue();
    } catch (err: any) {
      alert('Start Progress Failure: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenConfirmExec = (action: ActionLogItem) => {
    setSelectedAction(action);
    setIsConfirmExecOpen(true);
  };

  const handleConfirmExec = async (notes: string, role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN') => {
    if (!selectedAction) return;
    setIsSubmitting(true);
    try {
      await actionExecutionApi.confirmExecution(selectedAction.action_id, {
        dispatcher_id: 'USER-DISPATCHER-1',
        dispatcher_role: role,
        idempotency_key: 'EXEC-CONFIRM-' + safeUUID(),
        version_lock: selectedAction.version_lock,
        notes,
      });
      setIsConfirmExecOpen(false);
      await fetchActionQueue();
    } catch (err: any) {
      alert('Execution Confirmation Failure: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenReject = (action: ActionLogItem) => {
    setSelectedAction(action);
    setRejectDeferMode('REJECT');
    setIsRejectDeferOpen(true);
  };

  const handleOpenDefer = (action: ActionLogItem) => {
    setSelectedAction(action);
    setRejectDeferMode('DEFER');
    setIsRejectDeferOpen(true);
  };

  const handleConfirmRejectDefer = async (reasonCode: string, notes: string, retryAt?: string) => {
    if (!selectedAction) return;
    setIsSubmitting(true);
    try {
      if (rejectDeferMode === 'REJECT') {
        await actionExecutionApi.rejectRecommendation(selectedAction.action_id, {
          dispatcher_id: 'USER-DISPATCHER-1',
          dispatcher_role: 'DISPATCHER',
          idempotency_key: 'EXEC-REJECT-' + safeUUID(),
          version_lock: selectedAction.version_lock,
          reason_code: reasonCode,
          notes,
        });
      } else {
        await actionExecutionApi.deferRecommendation(selectedAction.action_id, {
          dispatcher_id: 'USER-DISPATCHER-1',
          dispatcher_role: 'DISPATCHER',
          idempotency_key: 'EXEC-DEFER-' + safeUUID(),
          version_lock: selectedAction.version_lock,
          reason_code: reasonCode,
          retry_at: retryAt,
          notes,
        });
      }
      setIsRejectDeferOpen(false);
      await fetchActionQueue();
    } catch (err: any) {
      alert('Action Failure: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewAudit = (action: ActionLogItem) => {
    setSelectedAction(action);
    setIsAuditOpen(true);
  };

  return (
    <DashboardSyncProvider onRefreshNeeded={fetchActionQueue}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Sub-Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconSupervisorDirectives className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Control Tower Actions &amp; Execution Canvas
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Real-time dispatcher decision support, execution tracking, and financial loss mitigation directives
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Filter Bar Integration */}
        <GlobalDashboardFilterBar />

      {/* Human-In-The-Loop Governance Banner & Action Generator Button */}
      <div className="bg-white border border-slate-200/90 rounded-lg p-4.5 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-md bg-blue-50 border border-blue-200 shrink-0 text-blue-700">
            <Info className="w-5 h-5" />
          </div>
          <div className="text-xs font-medium text-slate-600">
            <strong className="text-slate-900">Human-In-The-Loop Execution Guarantee:</strong> Recording dispatcher decisions and confirming operational execution does NOT trigger automatic external ERP write-backs. Dispatcher confirmations are logged for continuous learning.
          </div>
        </div>
        <button
          onClick={handleGenerateActions}
          disabled={isGenerating || !canExecuteActions}
          title={!canExecuteActions ? 'Requires Edit permission to re-evaluate action directives' : undefined}
          className="flex items-center gap-2 px-4 py-2 text-white text-xs font-bold rounded-md bg-blue-700 hover:bg-blue-800 shadow-xs transition disabled:opacity-50 disabled:cursor-not-allowed shrink-0 cursor-pointer"
        >
          <RefreshCw className={'w-3.5 h-3.5 ' + (isGenerating ? 'animate-spin' : '')} />
          {isGenerating ? 'Evaluating Pipeline...' : 'Re-evaluate Action Directives'}
        </button>
      </div>

      {/* Generation Progress Indicator Banner */}
      {generateProgress && (
        <div className="border border-emerald-300 bg-emerald-50 rounded-md p-3.5 mb-6 text-xs flex items-center gap-3 animate-pulse shadow-xs text-emerald-800">
          <RefreshCw className="w-4 h-4 animate-spin flex-shrink-0 text-emerald-700" />
          <div className="font-bold">{generateProgress}</div>
        </div>
      )}

      {/* Summary KPI Ribbon */}
      <ActionSummaryKPIRibbon actions={actions} isLoading={isLoading} onRefresh={fetchActionQueue} />

      {/* Filter Tabs & Queue Header */}
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 mb-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Filter className="w-4 h-4 shrink-0 text-slate-500" />
          <span className="text-xs font-bold uppercase shrink-0 text-slate-900">Triage State:</span>
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'ALL', label: 'All Directives' },
              { id: 'PENDING', label: 'Pending Action' },
              { id: 'ACCEPTED', label: 'Approved' },
              { id: 'IN_PROGRESS', label: 'In Progress' },
              { id: 'EXECUTED', label: 'Confirmed Executed' },
              { id: 'DEFERRED', label: 'Deferred' },
              { id: 'REJECTED', label: 'Rejected' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setStatusFilter(st.id)}
                className={
                  'px-3 py-1.5 text-xs font-bold rounded-md transition cursor-pointer ' +
                  (statusFilter === st.id
                    ? 'bg-blue-700 text-white shadow-xs'
                    : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-blue-700 border border-slate-200')
                }
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono font-medium text-slate-500">
          <div className="flex items-center gap-2">
            <span>Show:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="border border-slate-200 bg-white font-bold rounded-md px-2 py-1 text-slate-900"
            >
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
            </select>
          </div>
          <div>
            Showing <span className="font-bold text-slate-900 tabular-nums">{actions.length > 0 ? (currentPage - 1) * pageSize + 1 : 0}-{Math.min(actions.length, currentPage * pageSize)}</span> of <span className="font-bold text-slate-900 tabular-nums">{actions.length}</span>
          </div>
        </div>
      </div>

      {/* Error Message Display */}
      {error && (
        <div className="border border-rose-300 bg-rose-50 p-4 rounded-md mb-6 text-xs flex items-center gap-3 text-rose-800">
          <ShieldAlert className="w-5 h-5 flex-shrink-0 text-rose-700" />
          <div className="font-bold">{error}</div>
        </div>
      )}

      {/* Action Cards Queue Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-xs font-bold flex flex-col items-center gap-2 text-slate-500">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-700" />
          Fetching filter-scoped action queue from PostgreSQL DB...
        </div>
      ) : actions.length === 0 ? (
        <div className="bg-white border border-slate-200/90 rounded-lg p-12 text-center text-xs text-slate-500">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-700 opacity-80" />
          <p className="font-bold text-sm text-slate-900">No Action Recommendations in Current Filter Scope</p>
          <p className="mt-1 text-slate-600">All dispatches for plant <span className="font-bold text-blue-700 font-mono">{filters.plant_id}</span> are operating within standard parameters.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {actions
              .slice((currentPage - 1) * pageSize, currentPage * pageSize)
              .map((action) => (
                <ControlTowerActionCard
                  key={action.action_id}
                  action={action}
                  onAccept={handleOpenAccept}
                  onStartProgress={handleStartProgress}
                  onConfirmExecution={handleOpenConfirmExec}
                  onReject={handleOpenReject}
                  onDefer={handleOpenDefer}
                  onViewAudit={handleViewAudit}
                  readOnly={!canExecuteActions}
                />
              ))}
          </div>

          {/* Pagination Controls */}
          <div className="bg-white border border-slate-200/90 rounded-lg p-4 mt-6 flex items-center justify-between font-mono">
            <div className="text-xs text-slate-500">
              Page <span className="font-bold text-slate-900 tabular-nums">{currentPage}</span> of{' '}
              <span className="font-bold text-slate-900 tabular-nums">{Math.max(1, Math.ceil(actions.length / pageSize))}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                className="px-3 py-1.5 text-xs font-bold rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition hover:bg-slate-50 cursor-pointer shadow-xs"
              >
                Previous
              </button>
              <button
                disabled={currentPage >= Math.ceil(actions.length / pageSize)}
                onClick={() => setCurrentPage((prev) => Math.min(Math.ceil(actions.length / pageSize), prev + 1))}
                className="px-3 py-1.5 text-xs font-bold rounded-md border border-blue-700 bg-blue-700 text-white transition disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-800 cursor-pointer shadow-xs"
              >
                Next Page
              </button>
            </div>
          </div>
        </>
      )}

      {/* Action Execution Modals */}
      <AcceptActionModal
        action={selectedAction}
        isOpen={isAcceptOpen}
        onClose={() => setIsAcceptOpen(false)}
        onConfirm={handleConfirmAccept}
        isSubmitting={isSubmitting}
      />

      <ConfirmExecutionModal
        action={selectedAction}
        isOpen={isConfirmExecOpen}
        onClose={() => setIsConfirmExecOpen(false)}
        onConfirm={handleConfirmExec}
        isSubmitting={isSubmitting}
      />

      <RejectDeferModal
        action={selectedAction}
        isOpen={isRejectDeferOpen}
        mode={rejectDeferMode}
        onClose={() => setIsRejectDeferOpen(false)}
        onConfirm={handleConfirmRejectDefer}
        isSubmitting={isSubmitting}
      />

      <ActionAuditModal
        action={selectedAction}
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
      />
      </div>
    </DashboardSyncProvider>
  );
};

export const ControlTowerActionsPage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <ControlTowerActionsContent />
    </DashboardFilterProvider>
  );
};
