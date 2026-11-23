import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle } from 'lucide-react';
import { IconDispatchOptimization } from '../../../components/icons/LinealColorIcons';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { DashboardFilterProvider, useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { DispatchOptimizationGantt } from '../components/DispatchOptimization/DispatchOptimizationGantt';
import { env } from '../../../config/env';

const DispatchOptimizationDashboardContent: React.FC = () => {
  const { filters } = useDashboardFilters();

  const [readiness, setReadiness] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [ganttData, setGanttData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Re-fetch readiness, optimization run, and Gantt data when global filters change
  useEffect(() => {
    let isMounted = true;

    const fetchOptimizationState = async () => {
      setIsLoading(true);
      setActionSuccess(null);
      setActionError(null);
      setGanttData(null);
      setScenarios([]);

      try {
        const queryParams = new URLSearchParams();
        if (filters.plant_id) queryParams.set('plant_id', filters.plant_id);
        if (filters.customer_id) queryParams.set('customer_id', filters.customer_id);
        if (filters.dataset_type) queryParams.set('dataset_type', filters.dataset_type);

        const readinessRes = await fetch(`${env.VITE_API_BASE_URL}/dispatch-optimization/readiness?${queryParams.toString()}`);
        const readinessData = await readinessRes.json();

        if (!isMounted) return;
        setReadiness(readinessData);

        if (readinessData.status === 'NO_OBSERVATIONS') {
          setScenarios([]);
          setGanttData(null);
          setIsLoading(false);
          return;
        }

        const runRes = await fetch(`${env.VITE_API_BASE_URL}/dispatch-optimization/runs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filters: {
              plant_id: filters.plant_id || 'ALL',
              customer_id: filters.customer_id || 'ALL',
              dataset_type: filters.dataset_type || 'REAL_ONLY',
            },
            objective_config: { objective_type: 'BALANCED_OPERATIONS' },
          }),
        });

        const runData = await runRes.json();
        if (!isMounted) return;

        if (runData.scenarios && runData.scenarios.length > 0) {
          setScenarios(runData.scenarios);
          const recId = runData.recommended_scenario_id || runData.scenarios[0].scenario_id;
          setSelectedScenarioId(recId);

          const activeScenarioObj = runData.scenarios.find((s: any) => s.scenario_id === recId) || runData.scenarios[0];

          setGanttData({
            optimization_run_id: runData.optimization_run_id,
            scenario_id: recId,
            items: activeScenarioObj?.gantt_items || [],
          });
        }
        setIsStale(false);
      } catch (err: any) {
        if (isMounted) setActionError(err.message || 'Failed to load optimization workspace state.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchOptimizationState();

    return () => {
      isMounted = false;
    };
  }, [filters.plant_id, filters.customer_id, filters.dataset_type]);

  // Handle Planner Action Submission (ACCEPT, MODIFY, REJECT)
  const handlePlannerAction = async (actionType: 'ACCEPTED' | 'MODIFIED' | 'REJECTED') => {
    setActionSuccess(null);
    setActionError(null);

    if (isStale) {
      setActionError('Optimization plan is out of date — refresh optimization context.');
      return;
    }

    try {
      const activeScen = scenarios.find((s) => s.scenario_id === selectedScenarioId) || scenarios[0];
      const payload: any = {
        optimization_run_id: ganttData?.optimization_run_id || 'RUN-1001',
        scenario_id: selectedScenarioId,
        objective_type: activeScen?.objective_type || 'BALANCED_OPERATIONS',
        snapshot_hash: '01a068076c072bc5f4defbe5f1917e6ead8251421dda8f413aadba1f660d6c24',
        action_type: actionType,
      };

      if (actionType === 'MODIFIED') {
        payload.modified_parameters = { time_shift_mins: 15, note: 'Operator shift modification' };
      } else if (actionType === 'REJECTED') {
        payload.rejection_reason = 'PLANT_CAPACITY_LIMIT';
      }

      const res = await fetch(`${env.VITE_API_BASE_URL}/dispatch-optimization/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.status === 409) {
        setIsStale(true);
        setActionError('Optimization plan is out of date due to ERP dataset update.');
        return;
      }

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Planner action submission failed.');
      }

      const data = await res.json();
      setActionSuccess(`Decision ${data.record.action_id} successfully recorded! Decision: ${actionType}`);
    } catch (err: any) {
      setActionError(err.message || 'Action submission error.');
    }
  };

  const isActionsDisabled = isStale || isLoading || readiness?.status === 'NO_OBSERVATIONS' || !scenarios.length;

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800" data-testid="workspace-container">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
        <div className="flex items-center gap-3">
          <div className="shrink-0 flex items-center justify-center">
            <IconDispatchOptimization className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Dispatch Optimization Control Center
            </h1>
            <p className="text-xs font-medium text-slate-500">
              Real-Time Operational Readiness, Scenario Planning &amp; Cadence Optimization
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <SyncStatusHeaderBadge />
        </div>
      </div>

      {/* Reused Shared Global Dashboard Filter Bar */}
      <GlobalDashboardFilterBar />

      {/* Audit Confirmation / Error Messages */}
      {actionSuccess && (
        <div className="p-3 border rounded-md text-xs flex items-center gap-2 bg-emerald-50 border-emerald-200 text-emerald-750 font-medium" data-testid="action-success-banner">
          <CheckCircle size={16} />
          <span>{actionSuccess}</span>
        </div>
      )}
      {actionError && (
        <div className="p-3 border rounded-md text-xs flex items-center gap-2 bg-rose-50 border-rose-200 text-rose-750 font-medium" data-testid="action-error-banner">
          <XCircle size={16} />
          <span>{actionError}</span>
        </div>
      )}

      {/* Operator Decision Controls Bar */}
      <div className="p-4 rounded-lg border border-slate-200/90 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs" data-testid="planner-action-controls">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Optimization Governance</h3>
          <p className="text-[11px] text-slate-500 mt-0.5">Authorize or adjust the candidate departure pacing schedule</p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => handlePlannerAction('ACCEPTED')}
            disabled={isActionsDisabled}
            className="px-4 py-2 rounded-md font-bold text-xs bg-emerald-700 hover:bg-emerald-800 text-white shadow-xs disabled:opacity-40 disabled:cursor-not-allowed transition"
            data-testid="accept-action-btn"
          >
            Accept Scenario
          </button>
          <button
            onClick={() => handlePlannerAction('MODIFIED')}
            disabled={isActionsDisabled}
            className="px-4 py-2 rounded-md font-bold text-xs bg-blue-700 hover:bg-blue-800 text-white shadow-xs disabled:opacity-40 disabled:cursor-not-allowed transition"
            data-testid="modify-action-btn"
          >
            Modify Cadence
          </button>
          <button
            onClick={() => handlePlannerAction('REJECTED')}
            disabled={isActionsDisabled}
            className="px-4 py-2 rounded-md font-bold text-xs bg-rose-700 hover:bg-rose-800 text-white shadow-xs disabled:opacity-40 disabled:cursor-not-allowed transition"
            data-testid="reject-action-btn"
          >
            Reject Plan
          </button>
        </div>
      </div>

      {/* Main Gantt Timeline Composition Component */}
      <DispatchOptimizationGantt
        readiness={readiness}
        scenarios={scenarios}
        selectedScenarioId={selectedScenarioId}
        ganttData={ganttData}
        isLoading={isLoading}
        isStale={isStale}
        onScenarioSelect={(id) => setSelectedScenarioId(id)}
      />
    </div>
  );
};

export const DispatchOptimizationDashboardPage: React.FC = () => {
  return (
    <DashboardSyncProvider onRefreshNeeded={async () => {}}>
      <DashboardFilterProvider>
        <DispatchOptimizationDashboardContent />
      </DashboardFilterProvider>
    </DashboardSyncProvider>
  );
};

export default DispatchOptimizationDashboardPage;
