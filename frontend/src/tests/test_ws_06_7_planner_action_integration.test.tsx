import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DispatchOptimizationDashboardPage } from '../modules/operational_dashboard/pages/DispatchOptimizationDashboardPage';

describe('WS-06.7 Planner Action Integration Tests', () => {
  it('renders decision controls bar cleanly', () => {
    render(
      <MemoryRouter>
        <DispatchOptimizationDashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('planner-action-controls')).toBeDefined();
    expect(screen.getByTestId('accept-action-btn')).toBeDefined();
    expect(screen.getByTestId('modify-action-btn')).toBeDefined();
    expect(screen.getByTestId('reject-action-btn')).toBeDefined();
  });
});
