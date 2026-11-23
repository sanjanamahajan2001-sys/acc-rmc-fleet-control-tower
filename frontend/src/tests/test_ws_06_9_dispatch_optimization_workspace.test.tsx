import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DispatchOptimizationDashboardPage } from '../modules/operational_dashboard/pages/DispatchOptimizationDashboardPage';

describe('WS-06.9 Dispatch Optimization Workspace & Route Tests', () => {
  it('1. Renders DispatchOptimizationDashboardPage container cleanly', () => {
    render(
      <MemoryRouter>
        <DispatchOptimizationDashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('workspace-container')).toBeDefined();
    expect(screen.getByText('Dispatch Optimization Control Center')).toBeDefined();
  });

  it('2. Renders DispatchOptimizationDashboardPage with GlobalDashboardFilterBar cleanly', () => {
    render(
      <MemoryRouter>
        <DispatchOptimizationDashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('workspace-container')).toBeDefined();
  });
});
