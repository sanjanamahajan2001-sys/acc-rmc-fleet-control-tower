import { test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DispatchOptimizationGantt } from '../modules/operational_dashboard/components/DispatchOptimization/DispatchOptimizationGantt';

const mockScenario = {
  scenario_id: 'SCEN-001',
  scenario_name: 'Balanced Plan',
  objective_type: 'BALANCED_OPERATIONS',
  pareto_score: 95.0,
  is_recommended: true,
  constraint_violations_count: 0,
  constraint_notes: [],
  impact_matrix: {
    sla_compliance: { metric_name: 'SLA', observed_baseline: 80, optimized_value: 85, net_delta: 5, percentage_change: 6.2, unit: '%' },
    dispatch_accuracy_das: { metric_name: 'DAS', observed_baseline: 70, optimized_value: 75, net_delta: 5, percentage_change: 7.1, unit: '%' },
    cumulative_delay_hours: { metric_name: 'Delay', observed_baseline: 10, optimized_value: 8, net_delta: -2, percentage_change: -20, unit: 'hrs' },
    plant_holding_delay_hours: { metric_name: 'Holding', observed_baseline: 5, optimized_value: 3, net_delta: -2, percentage_change: -40, unit: 'hrs' },
    site_retention_delay_hours: { metric_name: 'Retention', observed_baseline: 3, optimized_value: 2, net_delta: -1, percentage_change: -33, unit: 'hrs' },
    sequence_variance_delay_hours: { metric_name: 'SeqVar', observed_baseline: 2, optimized_value: 1, net_delta: -1, percentage_change: -50, unit: 'hrs' },
  },
  gantt_items: [
    {
      dispatch_id: 'DSP-001',
      dispatch_number: 'DSP-1001',
      vehicle_id: 'GA01V1001',
      plant_id: 'ACC_VASCO',
      customer_id: 'CUST_AARA_HOTELS',
      raw_time_out: '08:00:00',
      raw_time_in: '10:00:00',
      baseline_time_out_iso: '2025-06-20T08:00:00Z',
      baseline_time_in_iso: '2025-06-20T10:00:00Z',
      recommended_time_out_iso: '2025-06-20T08:15:00Z',
      recommended_time_in_iso: '2025-06-20T10:15:00Z',
      time_shift_mins: 15,
      t1_transit_mins: 30,
      t2a_holding_mins: 10,
      t2c_retention_mins: 5,
      sequence_order: 1,
      recommendation_reason: {
        recommendation_reason_code: 'PLANT_HOLDING_BOTTLENECK_REDUCTION',
        explanation: 'Shift clears plant bottleneck',
        baseline_departure_iso: '2025-06-20T08:00:00Z',
        recommended_departure_iso: '2025-06-20T08:15:00Z',
        shift_minutes: 15,
        objective_type: 'BALANCED_OPERATIONS',
        constraints_satisfied: true,
        expected_sla_delta: 2.0,
        expected_delay_delta_hours: -0.5,
        solver_policy_version: 'v1.0.0-PROPOSED',
      },
    },
  ],
};

test('DispatchOptimizationGantt renders loading state cleanly', () => {
  render(<DispatchOptimizationGantt readiness={null} scenarios={[]} isLoading={true} />);
  expect(screen.getByTestId('gantt-loading')).toBeDefined();
});

test('DispatchOptimizationGantt renders NO_OBSERVATIONS zero state cleanly', () => {
  render(<DispatchOptimizationGantt readiness={{ status: 'NO_OBSERVATIONS' }} scenarios={[]} isLoading={false} />);
  expect(screen.getByTestId('gantt-no-observations')).toBeDefined();
});

test('DispatchOptimizationGantt renders timeline and impact matrix ribbon cleanly', () => {
  render(
    <DispatchOptimizationGantt
      readiness={{ status: 'READY' }}
      scenarios={[mockScenario]}
      selectedScenarioId="SCEN-001"
      ganttData={{ optimization_run_id: 'RUN-1', scenario_id: 'SCEN-001', items: mockScenario.gantt_items }}
      isLoading={false}
    />
  );
  expect(screen.getByTestId('gantt-container')).toBeDefined();
  expect(screen.getByTestId('impact-matrix-ribbon')).toBeDefined();
});
