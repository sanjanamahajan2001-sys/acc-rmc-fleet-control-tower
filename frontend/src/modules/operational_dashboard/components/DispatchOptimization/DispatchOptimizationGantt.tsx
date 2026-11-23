import React, { useMemo, useState } from 'react';
import { Info, ChevronLeft, ChevronRight, ArrowRight, CheckCircle2 } from 'lucide-react';
import { IconGanttSchedule } from '../../../../components/icons/LinealColorIcons';

export interface MetricDeltaDTO {
  metric_name: string;
  observed_baseline: number;
  optimized_value: number;
  net_delta: number;
  percentage_change: number;
  unit: string;
}

export interface BeforeAfterImpactMatrixDTO {
  sla_compliance: MetricDeltaDTO;
  dispatch_accuracy_das: MetricDeltaDTO;
  cumulative_delay_hours: MetricDeltaDTO;
  plant_holding_delay_hours: MetricDeltaDTO;
  site_retention_delay_hours: MetricDeltaDTO;
  sequence_variance_delay_hours: MetricDeltaDTO;
}

export interface RecommendationReasonDTO {
  recommendation_reason_code: string;
  explanation: string;
  baseline_departure_iso: string;
  recommended_departure_iso: string;
  shift_minutes: number;
  objective_type: string;
  constraints_satisfied: boolean;
  expected_sla_delta: number;
  expected_delay_delta_hours: number;
  solver_policy_version: string;
}

export interface DispatchGanttItemDTO {
  dispatch_id: string;
  dispatch_number: string;
  vehicle_id: string;
  plant_id: string;
  customer_id: string;
  raw_time_out: string;
  raw_time_in: string;
  baseline_time_out_iso: string;
  baseline_time_in_iso: string;
  recommended_time_out_iso: string;
  recommended_time_in_iso: string;
  time_shift_mins: number;
  t1_transit_mins: number;
  t2a_holding_mins: number;
  t2c_retention_mins: number;
  sequence_order: number;
  recommendation_reason?: RecommendationReasonDTO;
}

export interface CandidateScenarioDTO {
  scenario_id: string;
  scenario_name: string;
  objective_type: string;
  pareto_score: number;
  is_recommended: boolean;
  impact_matrix: BeforeAfterImpactMatrixDTO;
  constraint_violations_count: number;
  constraint_notes: string[];
  gantt_items?: DispatchGanttItemDTO[];
}

export interface DispatchOptimizationGanttProps {
  readiness: any;
  scenarios: CandidateScenarioDTO[];
  selectedScenarioId?: string;
  ganttData?: {
    optimization_run_id: string;
    scenario_id: string;
    items: DispatchGanttItemDTO[];
  } | null;
  isLoading?: boolean;
  isStale?: boolean;
  onScenarioSelect?: (scenarioId: string) => void;
}

const OPERATOR_REASON_CODE_MAP: Record<string, string> = {
  OPTIMAL_HISTORICAL_SPACING: 'Historical departure already satisfies pacing & queue constraints.',
  PLANT_HOLDING_BOTTLENECK_REDUCTION: 'Paced departure staggered to eliminate on-site mixer queue congestion.',
  DEPARTURE_GAP_SPACING_ENFORCED: 'Shifted forward to maintain guaranteed minimum spacing between trucks.',
};

export const DispatchOptimizationGantt: React.FC<DispatchOptimizationGanttProps> = ({
  readiness,
  scenarios,
  selectedScenarioId,
  ganttData,
  isLoading = false,
  isStale = false,
  onScenarioSelect,
}) => {
  const [expandedDispatchId, setExpandedDispatchId] = useState<string | null>(null);
  const [plantPages, setPlantPages] = useState<Record<string, number>>({});
  const pageSize = 8;

  const activeScenario = useMemo(() => {
    if (!scenarios || scenarios.length === 0) return null;
    if (!selectedScenarioId) return scenarios.find((s) => s.is_recommended) || scenarios[0];
    return scenarios.find((s) => s.scenario_id === selectedScenarioId) || scenarios[0];
  }, [scenarios, selectedScenarioId]);

  const items = useMemo(() => {
    return ganttData?.items || activeScenario?.gantt_items || [];
  }, [ganttData, activeScenario]);

  // Group real dispatches by plant location
  const plantGroups = useMemo(() => {
    const groups: Record<string, DispatchGanttItemDTO[]> = {};
    items.forEach((item) => {
      const p = item.plant_id || 'UNKNOWN';
      if (!groups[p]) groups[p] = [];
      groups[p].push(item);
    });
    return groups;
  }, [items]);

  const toggleExpand = (dispatchId: string) => {
    setExpandedDispatchId((prev) => (prev === dispatchId ? null : dispatchId));
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center bg-white border border-slate-200/90 rounded-lg shadow-2xs animate-pulse" data-testid="gantt-loading">
        <div className="w-8 h-8 border-2 border-blue-700 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs font-semibold text-slate-700">Evaluating Cadence Solver &amp; Optimization Scenarios...</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Simulating vehicle queue holding reduction</p>
      </div>
    );
  }

  if (readiness?.status === 'NO_OBSERVATIONS' || (!items.length && !isLoading)) {
    return (
      <div className="p-10 text-center bg-white border border-slate-200/90 rounded-lg shadow-2xs" data-testid="gantt-no-observations">
        <h3 className="text-sm font-bold text-slate-800 mb-1">NO OPTIMIZATION SCENARIOS AVAILABLE</h3>
        <p className="text-xs text-slate-500">No operational dispatches found for the selected filter scope.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="gantt-container">
      {/* Scenario Planning Header Container */}
      <div className="bg-white p-4 rounded-lg border border-slate-200/90 shadow-2xs space-y-3.5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <IconGanttSchedule className="w-5 h-5 shrink-0" />
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                Recommended Schedule vs. Baseline Comparison
              </h2>
              {isStale && (
                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                  Plan Outdated · Refresh Required
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Simulated cadence adjustments derived from ERP operational constraints and queue throughput
            </p>
          </div>

          {scenarios.length > 0 && (
            <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2.5 w-full md:w-auto min-w-0">
              <label className="text-xs font-semibold text-slate-600 shrink-0">Optimization Scenario:</label>
              <select
                value={activeScenario?.scenario_id || ''}
                onChange={(e) => onScenarioSelect && onScenarioSelect(e.target.value)}
                className="w-full sm:w-auto max-w-full truncate bg-slate-50 border border-slate-200 text-slate-900 text-xs rounded-lg px-3 py-1.5 font-semibold focus:outline-none focus:border-blue-600 shadow-2xs"
                data-testid="scenario-selector"
              >
                {scenarios.map((s) => (
                  <option key={s.scenario_id} value={s.scenario_id}>
                    {s.scenario_name} (Efficiency Score: {s.pareto_score})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Projected Impact Matrix Ribbon */}
        {activeScenario?.impact_matrix && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="impact-matrix-ribbon">
            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200/80">
              <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">SLA Compliance</div>
              <div className="text-lg font-extrabold text-slate-900 font-mono tabular-nums mt-0.5">
                {activeScenario.impact_matrix.sla_compliance.optimized_value}%
              </div>
              <div className="text-[10px] font-bold text-emerald-700 font-sans mt-0.5">
                +{activeScenario.impact_matrix.sla_compliance.net_delta}% vs Baseline
              </div>
            </div>

            <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200/80">
              <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">DAS Accuracy Score</div>
              <div className="text-lg font-extrabold text-slate-900 font-mono tabular-nums mt-0.5">
                {activeScenario.impact_matrix.dispatch_accuracy_das.optimized_value}%
              </div>
              <div className="text-[10px] font-bold text-blue-700 font-sans mt-0.5">
                +{activeScenario.impact_matrix.dispatch_accuracy_das.net_delta}% vs Baseline
              </div>
            </div>

            <div className="bg-slate-50/60 p-3 rounded-lg border border-slate-200/70">
              <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Delay Incurred</div>
              <div className="text-lg font-extrabold text-slate-900 font-mono mt-0.5">
                {activeScenario.impact_matrix.cumulative_delay_hours.optimized_value} hrs
              </div>
              <div className="text-[10px] font-bold text-emerald-700 font-sans mt-0.5">
                {activeScenario.impact_matrix.cumulative_delay_hours.net_delta} hrs vs Baseline
              </div>
            </div>

            <div className="bg-slate-50/60 p-3 rounded-lg border border-slate-200/70">
              <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Holding Delay</div>
              <div className="text-lg font-extrabold text-slate-900 font-mono mt-0.5">
                {activeScenario.impact_matrix.plant_holding_delay_hours.optimized_value} hrs
              </div>
              <div className="text-[10px] font-bold text-emerald-700 font-sans mt-0.5">
                {activeScenario.impact_matrix.plant_holding_delay_hours.net_delta} hrs vs Baseline
              </div>
            </div>

            <div className="bg-slate-50/60 p-3 rounded-lg border border-slate-200/70">
              <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Retention Delay</div>
              <div className="text-lg font-extrabold text-slate-900 font-mono mt-0.5">
                {activeScenario.impact_matrix.site_retention_delay_hours.optimized_value} hrs
              </div>
              <div className="text-[10px] font-bold text-emerald-700 font-sans mt-0.5">
                {activeScenario.impact_matrix.site_retention_delay_hours.net_delta} hrs vs Baseline
              </div>
            </div>

            <div className="bg-slate-50/60 p-3 rounded-lg border border-slate-200/70">
              <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Interval Variance</div>
              <div className="text-lg font-extrabold text-slate-900 font-mono mt-0.5">
                {activeScenario.impact_matrix.sequence_variance_delay_hours.optimized_value} hrs
              </div>
              <div className="text-[10px] font-bold text-emerald-700 font-sans mt-0.5">
                {activeScenario.impact_matrix.sequence_variance_delay_hours.net_delta} hrs vs Baseline
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Paginated Plant Group Schedule Comparison Matrix */}
      <div className="space-y-4" data-testid="paginated-gantt-container">
        {Object.entries(plantGroups).map(([plantId, plantItems]) => {
          const totalItems = plantItems.length;
          const totalPlantPages = Math.ceil(totalItems / pageSize) || 1;
          const currentPlantPage = plantPages[plantId] || 1;
          const startIndex = (currentPlantPage - 1) * pageSize;
          const paginatedItems = plantItems.slice(startIndex, startIndex + pageSize);

          const handlePageChange = (newPage: number) => {
            setPlantPages((prev) => ({
              ...prev,
              [plantId]: Math.max(1, Math.min(totalPlantPages, newPage)),
            }));
          };

          return (
            <div
              key={plantId}
              className="bg-white rounded-lg border border-slate-200/90 shadow-xs overflow-hidden"
              data-testid={`plant-group-${plantId}`}
            >
              {/* Plant Header */}
              <div className="px-5 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Plant Origin: <span className="text-blue-700">{plantId}</span> ({totalItems.toLocaleString('en-IN')} Dispatches)
                </h3>

                {/* Pagination Controls */}
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="font-mono text-[11px]">
                    Page <strong className="text-slate-900">{currentPlantPage}</strong> of{' '}
                    <strong className="text-slate-900">{totalPlantPages}</strong>
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handlePageChange(currentPlantPage - 1)}
                      disabled={currentPlantPage === 1}
                      className="p-1 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition"
                      title="Previous Page"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handlePageChange(currentPlantPage + 1)}
                      disabled={currentPlantPage === totalPlantPages}
                      className="p-1 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition"
                      title="Next Page"
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Visual Before vs. After Trip Schedule Rows */}
              <div className="p-4 space-y-2.5">
                {paginatedItems.map((item) => {
                  const isExpanded = expandedDispatchId === item.dispatch_id;
                  const recTimeStr = item.recommended_time_out_iso.split('T')[1]?.replace('Z', '') || '08:15:00';
                  const shiftMins = item.time_shift_mins ?? 0;

                  return (
                    <div
                      key={item.dispatch_id}
                      className="border border-slate-200/80 rounded-md bg-white overflow-hidden transition-all hover:border-slate-300"
                      data-testid={`dispatch-item-${item.dispatch_id}`}
                    >
                      {/* Trip Row Bar */}
                      <div className="p-3.5 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                        {/* Trip Info */}
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 rounded-md bg-slate-100 border border-slate-200 flex items-center justify-center font-mono font-bold text-xs text-slate-700 shrink-0">
                            #{item.sequence_order}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-slate-900 text-xs">{item.dispatch_number}</span>
                              <span className="px-1.5 py-0.5 rounded font-mono text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                                {item.vehicle_id}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-500 font-medium truncate max-w-sm mt-0.5">
                              {item.customer_name || item.customer_id}
                            </div>
                          </div>
                        </div>

                        {/* Side-by-Side Before -> After Time Comparison */}
                        <div className="flex flex-wrap items-center gap-3 sm:gap-6 justify-between lg:justify-end">
                          <div className="flex items-center gap-2 text-xs font-mono bg-slate-50 px-3 py-1.5 rounded-md border border-slate-200/60">
                            <div>
                              <span className="text-[9px] uppercase font-bold text-slate-400 block font-sans">Baseline Out</span>
                              <span className="text-slate-700 font-semibold">{item.raw_time_out}</span>
                            </div>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                            <div>
                              <span className="text-[9px] uppercase font-bold text-blue-700 block font-sans">Optimized Out</span>
                              <span className="text-blue-700 font-bold">{recTimeStr}</span>
                            </div>
                          </div>

                          {/* Shift Badge */}
                          <span
                            className={`px-2 py-1 rounded text-[11px] font-bold font-mono border ${
                              shiftMins > 0
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            }`}
                          >
                            {shiftMins > 0 ? `+${shiftMins}m shift` : 'On Schedule'}
                          </span>

                          {/* Expandable Why Button */}
                          {item.recommendation_reason && (
                            <button
                              onClick={() => toggleExpand(item.dispatch_id)}
                              className={`px-2.5 py-1 rounded-md text-[11px] font-bold border transition flex items-center gap-1 ${
                                isExpanded
                                  ? 'bg-blue-700 text-white border-blue-700'
                                  : 'bg-white border-slate-200 text-blue-700 hover:bg-slate-50'
                              }`}
                              title="View Optimization Rationale"
                              data-testid={`why-btn-${item.dispatch_id}`}
                            >
                              <Info size={12} />
                              <span>{isExpanded ? 'Hide Rationale' : 'Why?'}</span>
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Inline Expanded Rationale Details */}
                      {isExpanded && item.recommendation_reason && (
                        <div className="p-4 border-t border-slate-100 bg-slate-50/70 space-y-2 text-xs">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-700">
                            <div>
                              <span className="text-[10px] font-bold uppercase text-slate-400 block">Pacing Decision:</span>
                              <span className="font-semibold text-slate-900">
                                {OPERATOR_REASON_CODE_MAP[item.recommendation_reason.recommendation_reason_code] ||
                                  item.recommendation_reason.explanation}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] font-bold uppercase text-slate-400 block">Expected Delay Recovery:</span>
                              <span className="font-mono font-bold text-emerald-700">
                                {item.recommendation_reason.expected_delay_delta_hours} hrs delay reduction
                              </span>
                            </div>
                          </div>
                          <p className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-200/60">
                            &ldquo;{item.recommendation_reason.explanation}&rdquo;
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
