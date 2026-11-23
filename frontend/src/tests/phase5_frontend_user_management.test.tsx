import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { env } from '../config/env';

import { useAuthStore } from '../store/auth';
import { ForcePasswordChangePage } from '../auth/ForcePasswordChangePage';
import { UserManagementPage } from '../modules/settings/pages/UserManagementPage';
import { ProtectedRoute } from '../auth/ProtectedRoute';

describe('Phase 5 Frontend Integration Suite', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ token: null, user: null });
    vi.restoreAllMocks();
  });

  it('ForcePasswordChangePage renders password policy requirements and handles submit', async () => {
    useAuthStore.setState({
      token: 'restricted_test_token',
      user: { sub: 'test-user-id', username: 'tempuser', auth_stage: 'PASSWORD_CHANGE_REQUIRED', must_change_password: true },
    });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        data: {
          access_token: 'fresh_normal_token',
          auth_stage: 'NORMAL',
          user: { id: 'test-user-id', username: 'tempuser', auth_stage: 'NORMAL', must_change_password: false },
        },
      }),
    });

    render(
      <MemoryRouter initialEntries={['/auth/force-password-change']}>
        <Routes>
          <Route path="/auth/force-password-change" element={<ForcePasswordChangePage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Mandatory Password Change/i)).toBeInTheDocument();
    expect(screen.getByText(/Min 8 characters/i)).toBeInTheDocument();

    const inputs = screen.getAllByPlaceholderText(/password/i);
    const newPassInput = inputs[0];
    const confirmPassInput = inputs[1];

    fireEvent.change(newPassInput, { target: { value: 'NewStrongPass123!' } });
    fireEvent.change(confirmPassInput, { target: { value: 'NewStrongPass123!' } });

    const submitBtn = screen.getByRole('button', { name: /Save New Password/i });
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        `${env.VITE_API_BASE_URL}/auth/change-password`,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ Authorization: 'Bearer restricted_test_token' }),
        })
      );
      expect(useAuthStore.getState().token).toBe('fresh_normal_token');
    });
  });

  it('ProtectedRoute redirects user with PASSWORD_CHANGE_REQUIRED stage to /auth/force-password-change', () => {
    useAuthStore.setState({
      token: 'restricted_token',
      user: { sub: 'user-id', auth_stage: 'PASSWORD_CHANGE_REQUIRED', must_change_password: true },
    });

    render(
      <MemoryRouter initialEntries={['/settings/users']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/settings/users" element={<div>Protected User Workspace</div>} />
          </Route>
          <Route path="/auth/force-password-change" element={<div>Forced Password Redirect Landing Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Forced Password Redirect Landing Page/i)).toBeInTheDocument();
    expect(screen.queryByText(/Protected User Workspace/i)).not.toBeInTheDocument();
  });

  it('UserManagementPage renders user directory table and triggers user creation modal', async () => {
    useAuthStore.setState({
      token: 'admin_test_token',
      user: { sub: 'admin-id', username: 'admin', is_superuser: true, roles: ['Administrator'] },
    });

    global.fetch = vi.fn().mockImplementation(() => {

      return Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            items: [
              {
                id: 'u-101',
                username: 'operator1',
                email: 'op1@fleetcontrol.io',
                full_name: 'Operator One',
                is_active: true,
                is_superuser: false,
                must_change_password: false,
                auth_stage: 'NORMAL',
                roles: ['Plant Dispatcher'],
                plant_scopes: [{ id: 'p1', code: 'PLANT-001', name: 'Plant A' }],
                last_login_at: '2026-08-20T10:00:00Z',
              },
            ],
            total: 1,
            page: 1,
            size: 15,
            pages: 1,
          },
        }),
      });
    });


    render(
      <MemoryRouter>
        <UserManagementPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('operator1')).toBeInTheDocument();
    expect(screen.getByText('op1@fleetcontrol.io')).toBeInTheDocument();
    expect(screen.getAllByText('Plant Dispatcher').length).toBeGreaterThan(0);


    // Click Create New User button
    const createBtn = screen.getByRole('button', { name: /Create New User/i });
    fireEvent.click(createBtn);

    expect(screen.getByText(/Create New Platform User/i)).toBeInTheDocument();

  });
});
