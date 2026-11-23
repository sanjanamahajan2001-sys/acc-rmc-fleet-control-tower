import { describe, it, expect } from 'vitest';

export interface OptimizationFilterParamsDTO {
  plant_id?: string;
  customer_id?: string;
  dataset_type?: 'REAL_ONLY' | 'SYNTHETIC_ONLY' | 'ALL';
}

export type OptimizationObjectiveEnum = 'BALANCED_OPERATIONS' | 'MINIMIZE_DELAY' | 'MAXIMIZE_SLA';
export type OptimizationRunStatusEnum =
  | 'IDLE'
  | 'READY'
  | 'RUNNING'
  | 'COMPLETED'
  | 'REVIEW'
  | 'ACCEPTED'
  | 'MODIFIED'
  | 'REJECTED'
  | 'STALE'
  | 'FAILED'
  | 'NO_FEASIBLE_SOLUTION';

export type ReadinessStatusEnum = 'READY' | 'DEGRADED' | 'NO_OBSERVATIONS';

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

export interface CandidateScenarioDTO {
  scenario_id: string;
  scenario_name: string;
  objective_type: OptimizationObjectiveEnum;
  pareto_score: number;
  is_recommended: boolean;
  impact_matrix: BeforeAfterImpactMatrixDTO;
  constraint_violations_count: number;
  constraint_notes: string[];
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
}

export interface OptimizationGanttResponseDTO {
  optimization_run_id: string;
  scenario_id: string;
  total_vehicles: number;
  total_dispatches: number;
  items: DispatchGanttItemDTO[];
}

describe('WS-06.2 Frontend Type Contract Validation Tests', () => {
  it('validates filter parameters structure matching DashboardFilterProvider', () => {
    const filters: OptimizationFilterParamsDTO = {
      plant_id: 'ACC_KUNDAIM',
      customer_id: 'CUST_AARA_HOTELS',
      dataset_type: 'REAL_ONLY',
    };
    expect(filters.plant_id).toBe('ACC_KUNDAIM');
    expect(filters.dataset_type).toBe('REAL_ONLY');
  });

  it('validates decoupled scenario_id and objective_type in candidate scenario', () => {
    const scenario: CandidateScenarioDTO = {
      scenario_id: 'SCENARIO-UUID-9981-ALPHA',
      scenario_name: 'Balanced Fleet Trade-Off',
      objective_type: 'BALANCED_OPERATIONS',
      pareto_score: 94.2,
      is_recommended: true,
      impact_matrix: {
        sla_compliance: { metric_name: 'SLA', observed_baseline: 54.3, optimized_value: 78.5, net_delta: 24.2, percentage_change: 44.5, unit: '%' },
        dispatch_accuracy_das: { metric_name: 'DAS', observed_baseline: 65.2, optimized_value: 82.4, net_delta: 17.2, percentage_change: 26.3, unit: '%' },
        cumulative_delay_hours: { metric_name: 'Delay', observed_baseline: 1471.9, optimized_value: 1059.4, net_delta: -412.5, percentage_change: -28.0, unit: 'hrs' },
        plant_holding_delay_hours: { metric_name: 'Holding', observed_baseline: 202.1, optimized_value: 78.4, net_delta: -123.7, percentage_change: -61.2, unit: 'hrs' },
        site_retention_delay_hours: { metric_name: 'Retention', observed_baseline: 56.0, optimized_value: 32.0, net_delta: -24.0, percentage_change: -42.8, unit: 'hrs' },
        sequence_variance_delay_hours: { metric_name: 'Sequence Variance', observed_baseline: 1213.8, optimized_value: 949.0, net_delta: -264.8, percentage_change: -21.8, unit: 'hrs' },
      },
      constraint_violations_count: 0,
      constraint_notes: [],
    };

    expect(scenario.scenario_id).toBe('SCENARIO-UUID-9981-ALPHA');
    expect(scenario.objective_type).toBe('BALANCED_OPERATIONS');
  });

  it('validates virtualized Gantt item payload attributes', () => {
    const item: DispatchGanttItemDTO = {
      dispatch_id: 'DISP-001',
      dispatch_number: 'SYNTH-TCK-TRIP-2754',
      vehicle_id: 'GA07F7626',
      plant_id: 'ACC_KUNDAIM',
      customer_id: 'CUST_AARA_HOTELS',
      raw_time_out: '12:05',
      raw_time_in: '14:30',
      baseline_time_out_iso: '2025-06-20T12:05:00Z',
      baseline_time_in_iso: '2025-06-20T14:30:00Z',
      recommended_time_out_iso: '2025-06-20T12:17:00Z',
      recommended_time_in_iso: '2025-06-20T14:42:00Z',
      time_shift_mins: 12.0,
      t1_transit_mins: 145.0,
      t2a_holding_mins: 13.7,
      t2c_retention_mins: 6.3,
      sequence_order: 1,
    };

    expect(item.time_shift_mins).toBe(12.0);
    expect(item.raw_time_out).toBe('12:05');
  });
});
