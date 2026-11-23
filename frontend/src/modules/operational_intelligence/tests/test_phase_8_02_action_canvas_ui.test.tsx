import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { ControlTowerActionsPage } from '../pages/ControlTowerActionsPage';
import { actionExecutionApi, ActionLogItem } from '../api/actionExecutionApi';

vi.mock('../api/actionExecutionApi', () => ({
  actionExecutionApi: {
    getActionQueue: vi.fn(),
    acceptRecommendation: vi.fn(),
    startProgress: vi.fn(),
    confirmExecution: vi.fn(),
    rejectRecommendation: vi.fn(),
    deferRecommendation: vi.fn(),
  },
}));

const mockActions: ActionLogItem[] = [
  {
    action_id: 'ACT-001',
    recommendation_id: 'REC-001',
    prediction_snapshot_id: 'SNAP-001',
    model_family: 'delay_regressor',
    model_version: 'v1.1.0-candidate-ds-fsv1-prom',
    dataset_id: 'DS-20260805-001',
    operation_date: '2026-08-19',
    plant_code: 'ACC_NESSAI',
    customer_code: 'CUST-001',
    dispatch_id: 'DISP-001',
    dispatch_code: 'SYNTH-TCK-TRIP-1',
    action_type: 'STAGGER_LOADING',
    action_parameters: { offset_mins: 15 },
    predicted_risk_exposure_inr: 2500,
    estimated_avoided_exposure_inr: 2125,
    actual_avoided_loss_inr: null,
    action_status: 'PENDING',
    dispatcher_id: null,
    dispatcher_role: null,
    dispatcher_notes: null,
    reason_code: null,
    decision_timestamp: null,
    accepted_at: null,
    started_at: null,
    execution_confirmed_at: null,
    rejected_at: null,
    deferred_at: null,
    version_lock: 1,
    idempotency_key: 'IDEMP-001',
  },
  {
    action_id: 'ACT-002',
    recommendation_id: 'REC-002',
    prediction_snapshot_id: 'SNAP-002',
    model_family: 'turnaround_regressor',
    model_version: 'v1.1.0-candidate-ds-fsv1-prom',
    dataset_id: 'DS-20260805-001',
    operation_date: '2026-08-19',
    plant_code: 'ACC_NESSAI',
    customer_code: 'CUST-002',
    dispatch_id: 'DISP-002',
    dispatch_code: 'SYNTH-TCK-TRIP-2',
    action_type: 'TRANSIT_BUFFER',
    action_parameters: { buffer_mins: 20 },
    predicted_risk_exposure_inr: 3000,
    estimated_avoided_exposure_inr: 2550,
    actual_avoided_loss_inr: null,
    action_status: 'ACCEPTED',
    dispatcher_id: 'DISPATCHER-1',
    dispatcher_role: 'DISPATCHER',
    dispatcher_notes: 'Holding transit buffer',
    reason_code: null,
    decision_timestamp: '2026-08-19T10:00:00Z',
    accepted_at: '2026-08-19T10:00:00Z',
    started_at: null,
    execution_confirmed_at: null,
    rejected_at: null,
    deferred_at: null,
    version_lock: 2,
    idempotency_key: 'IDEMP-002',
  },
];

const renderComponent = () =>
  render(
    <BrowserRouter>
      <ControlTowerActionsPage />
    </BrowserRouter>
  );

describe('Phase 8 WS8.2 Control Tower Action Execution Canvas UI Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (actionExecutionApi.getActionQueue as any).mockResolvedValue({
      total_count: mockActions.length,
      items: mockActions,
      filter_scope: { plant_id: 'ACC_NESSAI', customer_id: 'ALL', dataset_type: 'ALL' },
    });
  });

  it('UI-01 & UI-20 & UI-23: Renders Action Queue with Financial Terminology & HITL Guarantee', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText(/Control Tower Decision & Action Execution Canvas/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Estimated Avoided Exposure/i)).toBeInTheDocument();
    expect(screen.getByText(/Human-In-The-Loop Execution Guarantee/i)).toBeInTheDocument();
    expect(screen.queryByText(/Actual Realized Savings Claimed/i)).not.toBeInTheDocument();
  });

  it('UI-06: Displays PENDING Action controls (Accept Intent, Reject, Defer)', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText(/SYNTH-TCK-TRIP-1/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Accept Intent/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Reject$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Defer$/i })).toBeInTheDocument();
  });

  it('UI-07 & UI-08: Displays ACCEPTED Action controls (Start Progress, Confirm Execution)', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText(/SYNTH-TCK-TRIP-2/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Start Progress/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Confirm Execution/i })).toBeInTheDocument();
  });

  it('UI-12: Opens Accept Confirmation Modal and triggers backend accept API', async () => {
    (actionExecutionApi.acceptRecommendation as any).mockResolvedValue({
      success: true,
      message: 'Accepted',
      action: { ...mockActions[0], action_status: 'ACCEPTED' },
      is_idempotent_replay: false,
    });

    renderComponent();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Accept Intent/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Accept Intent/i }));
    expect(screen.getByText(/Approve Operational Recommendation Intent/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Confirm Intent Approval/i }));
    await waitFor(() => {
      expect(actionExecutionApi.acceptRecommendation).toHaveBeenCalledWith(
        'ACT-001',
        expect.objectContaining({
          dispatcher_role: 'DISPATCHER',
        })
      );
    });
  });

  it('UI-21: Opens Full Lineage Audit Modal and displays prediction details', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getAllByText(/View Full Lineage/i)[0]).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByText(/View Full Lineage/i)[0]);
    expect(screen.getByText(/End-to-End Decision & Lineage Traceability Audit/i)).toBeInTheDocument();
    expect(screen.getByText(/RATE_SPECIFICATION_GLOBAL_V1/i)).toBeInTheDocument();
  });
});
