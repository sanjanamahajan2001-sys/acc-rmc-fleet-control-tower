import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../app/App';
import { useAuthStore } from '../store/auth';

describe('Frontend Application Platform Bootstrap', () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth('mock_token_123', {
      sub: 'user_1',
      jti: 'jti_1',
      type: 'access',
      exp: 9999999999,
      iat: 1000000000,
    });
  });

  it('renders application shell layout without crashing when authenticated', () => {
    render(<App />);
    const matches = screen.getAllByText(/Fleet Control Tower/i);
    expect(matches.length).toBeGreaterThan(0);
    const ctrlTowerMatches = screen.getAllByText(/CONTROL TOWER/i);
    expect(ctrlTowerMatches.length).toBeGreaterThan(0);
  });
});
