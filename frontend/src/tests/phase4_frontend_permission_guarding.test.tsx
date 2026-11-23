import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePermissions } from '../hooks/usePermissions';
import { useAuthStore } from '../store/auth';

describe('Phase 4: Section-Based Permission Guarding', () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth();
  });

  it('Superuser has full edit and view access across all 14 sections', () => {
    act(() => {
      useAuthStore.getState().setAuth('dummy-token', {
        id: 'admin-1',
        username: 'admin',
        is_superuser: true,
        roles: ['Administrator'],
      });
    });

    const { result } = renderHook(() => usePermissions());
    expect(result.current.isSuperuser).toBe(true);
    expect(result.current.isRestricted).toBe(false);

    // Can access and edit all sections
    expect(result.current.canAccess('platform_home', 'view')).toBe(true);
    expect(result.current.canAccess('erp_import', 'edit')).toBe(true);
    expect(result.current.canAccess('settings', 'edit')).toBe(true);
    expect(result.current.canAccess('user_management', 'edit')).toBe(true);
    expect(result.current.canEdit('control_tower_actions')).toBe(true);
  });

  it('Restricted Demo Operator has view-only on ops and none on settings/erp_import', () => {
    act(() => {
      useAuthStore.getState().setAuth('demo-token', {
        id: 'demo-user-1',
        username: 'demo_operator',
        is_superuser: false,
        roles: [],
        section_permissions: {
          platform_home: 'view',
          site_dashboard: 'view',
          overall_dashboard: 'view',
          dispatch_analysis: 'view',
          dispatch_optimization: 'view',
          operational_intelligence: 'view',
          predictive_intelligence: 'view',
          control_tower_actions: 'view',
          alerts: 'view',
          reports: 'view',
          erp_import: 'none',
          erp_explorer: 'view',
          settings: 'none',
          user_management: 'none',
        },
      });
    });

    const { result } = renderHook(() => usePermissions());
    expect(result.current.isSuperuser).toBe(false);
    expect(result.current.isRestricted).toBe(true);

    // Operations viewing allowed
    expect(result.current.canView('platform_home')).toBe(true);
    expect(result.current.canView('site_dashboard')).toBe(true);
    expect(result.current.canView('control_tower_actions')).toBe(true);

    // Action execution / editing denied
    expect(result.current.canEdit('control_tower_actions')).toBe(false);

    // Completely restricted sections
    expect(result.current.canAccess('erp_import', 'view')).toBe(false);
    expect(result.current.canAccess('erp_import', 'edit')).toBe(false);
    expect(result.current.canAccess('settings', 'view')).toBe(false);
    expect(result.current.canAccess('user_management', 'view')).toBe(false);
  });

  it('Edit permission inherently implies View permission', () => {
    act(() => {
      useAuthStore.getState().setAuth('operator-token', {
        id: 'operator-1',
        username: 'custom_operator',
        is_superuser: false,
        roles: [],
        section_permissions: {
          control_tower_actions: 'edit',
          platform_home: 'none',
        },
      });
    });

    const { result } = renderHook(() => usePermissions());

    // Edit implies view
    expect(result.current.canEdit('control_tower_actions')).toBe(true);
    expect(result.current.canView('control_tower_actions')).toBe(true);

    // None denies both
    expect(result.current.canView('platform_home')).toBe(false);
    expect(result.current.canEdit('platform_home')).toBe(false);
  });

  it('Fallback defaults are safely applied when section_permissions is not configured', () => {
    act(() => {
      useAuthStore.getState().setAuth('legacy-token', {
        id: 'legacy-user-1',
        username: 'legacy_user',
        is_superuser: false,
        roles: [],
      });
    });

    const { result } = renderHook(() => usePermissions());

    // Operational default is view
    expect(result.current.canView('platform_home')).toBe(true);
    expect(result.current.canView('site_dashboard')).toBe(true);

    // Sensitive default is none
    expect(result.current.canView('settings')).toBe(false);
    expect(result.current.canView('user_management')).toBe(false);
    expect(result.current.canView('erp_import')).toBe(false);
  });
});
