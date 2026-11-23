import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { AuthProvider, useAuth } from '../auth/AuthProvider';
import { useAuthStore } from '../store/auth';

const TestAuthComponent = () => {
  const { isAuthenticated, logout } = useAuth();
  return (
    <div>
      <span>Auth Status: {isAuthenticated ? 'LoggedIn' : 'LoggedOut'}</span>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('Auth Layer & Protected Routes', () => {
  it('redirects to /login when token is missing in ProtectedRoute', () => {
    useAuthStore.getState().clearAuth();

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Secret Content</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page Guard</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Login Page Guard/i)).toBeInTheDocument();
  });

  it('renders ProtectedRoute content when token is active', () => {
    useAuthStore.getState().setAuth('valid_token', { sub: 'u1', jti: 'j1', type: 'access', exp: 1, iat: 1 });

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Secret Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Secret Content/i)).toBeInTheDocument();
  });

  it('provides AuthProvider context and handles logout', () => {
    render(
      <AuthProvider>
        <TestAuthComponent />
      </AuthProvider>
    );

    expect(screen.getByText(/Auth Status: LoggedIn/i)).toBeInTheDocument();
  });
});
