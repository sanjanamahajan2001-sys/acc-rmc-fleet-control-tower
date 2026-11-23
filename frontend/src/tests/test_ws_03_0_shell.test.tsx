import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OverallDashboardPage } from '../modules/operational_dashboard/pages/OverallDashboardPage';
import { useAuthStore } from '../store/auth';

describe('WS-03.0 Core Shell & Global Filter Integration Tests', () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth('test_token_123', {
      sub: 'test_operator_1',
      jti: 'jti_test',
      type: 'access',
      exp: 9999999999,
      iat: 1000000000,
    });
  });

  it('renders Overall Dashboard Shell with shared top bar and filter bar', async () => {
    render(
      <MemoryRouter initialEntries={['/overall-dashboard']}>
        <OverallDashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Overall Operational Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Executive Fleet Command Tower/i)).toBeInTheDocument();
    expect(screen.getByText(/Plant Selection/i)).toBeInTheDocument();
    expect(screen.getByText(/Customer Filter/i)).toBeInTheDocument();
    expect(screen.getByText(/Dataset Scope/i)).toBeInTheDocument();
  });
});
