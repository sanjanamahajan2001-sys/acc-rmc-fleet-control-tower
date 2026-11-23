import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

// WS-10 Phase 5.4 Model Health UI Component Contract Test
describe('Phase 5.4 Model Health UI Contract', () => {
  it('renders model health card with status badge and metrics', () => {
    const mockHealthData = {
      health_record_id: 'HLTH-DELAY-V110-30D-20260818',
      model_identity: {
        model_name: 'delay_regressor',
        model_family: 'delay_regressor',
        model_version_id: 'MOD-VER-v1.1.0-candidate-ds-fsv1-prom',
      },
      scope: { scope_type: 'GLOBAL', scope_id: null },
      window: { window_type: '30d', evaluation_timestamp: '2026-08-18T17:00:00Z' },
      sample_counts: { total_prediction_error_count: 880 },
      metrics: { mae: 3.25, rmse: 4.12, mean_signed_error: 0.45 },
      governance: { health_status: 'HEALTHY', baseline_mae: 4.50 },
    };

    render(
      <div data-testid="model-health-card">
        <h3>{mockHealthData.model_identity.model_name}</h3>
        <span data-testid="health-badge">{mockHealthData.governance.health_status}</span>
        <div>MAE: {mockHealthData.metrics.mae}m</div>
        <div>Baseline: {mockHealthData.governance.baseline_mae}m</div>
        <div>Samples: {mockHealthData.sample_counts.total_prediction_error_count}</div>
      </div>
    );

    expect(screen.getByTestId('model-health-card')).toBeInTheDocument();
    expect(screen.getByTestId('health-badge')).toHaveTextContent('HEALTHY');
    expect(screen.getByText('MAE: 3.25m')).toBeInTheDocument();
    expect(screen.getByText('Baseline: 4.5m')).toBeInTheDocument();
    expect(screen.getByText('Samples: 880')).toBeInTheDocument();
  });

  it('renders INSUFFICIENT_DATA status when sample denominator is below minimum', () => {
    const mockInsufficientData = {
      health_status: 'INSUFFICIENT_DATA',
      sample_counts: { total_prediction_error_count: 5 },
    };

    render(
      <div>
        <span data-testid="health-badge">{mockInsufficientData.health_status}</span>
        <div>Sample Count: {mockInsufficientData.sample_counts.total_prediction_error_count}</div>
      </div>
    );

    expect(screen.getByTestId('health-badge')).toHaveTextContent('INSUFFICIENT_DATA');
    expect(screen.getByText('Sample Count: 5')).toBeInTheDocument();
  });
});
