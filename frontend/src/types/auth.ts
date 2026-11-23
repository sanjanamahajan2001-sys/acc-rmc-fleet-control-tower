export type PlatformSectionKey =
  | 'platform_home'
  | 'site_dashboard'
  | 'overall_dashboard'
  | 'dispatch_analysis'
  | 'dispatch_optimization'
  | 'operational_intelligence'
  | 'predictive_intelligence'
  | 'control_tower_actions'
  | 'alerts'
  | 'reports'
  | 'erp_import'
  | 'erp_explorer'
  | 'settings'
  | 'user_management';

export type SectionAccessLevel = 'none' | 'view' | 'edit';

export type SectionPermissionsMap = Record<PlatformSectionKey, SectionAccessLevel>;

export const PLATFORM_SECTIONS: PlatformSectionKey[] = [
  'platform_home',
  'site_dashboard',
  'overall_dashboard',
  'dispatch_analysis',
  'dispatch_optimization',
  'operational_intelligence',
  'predictive_intelligence',
  'control_tower_actions',
  'alerts',
  'reports',
  'erp_import',
  'erp_explorer',
  'settings',
  'user_management',
];

export const PLATFORM_SECTION_LABELS: Record<PlatformSectionKey, string> = {
  platform_home: 'Platform Home',
  site_dashboard: 'Site Dashboard',
  overall_dashboard: 'Overall Dashboard',
  dispatch_analysis: 'Dispatch Analysis',
  dispatch_optimization: 'Dispatch Optimization',
  operational_intelligence: 'Operational Intelligence',
  predictive_intelligence: 'Predictive Intelligence',
  control_tower_actions: 'Control Tower Actions',
  alerts: 'Alert Center',
  reports: 'Reports & Exports',
  erp_import: 'ERP Import',
  erp_explorer: 'ERP Data Explorer',
  settings: 'Settings Center',
  user_management: 'User Management',
};

export interface UserClaims {
  id?: string;
  sub?: string;
  username?: string;
  email?: string;
  full_name?: string | null;
  jti?: string;
  type?: 'access' | 'refresh';
  tenant_id?: string | null;
  plant_id?: string | null;
  token_version?: number;
  auth_stage?: 'NORMAL' | 'PASSWORD_CHANGE_REQUIRED' | string;
  must_change_password?: boolean;
  is_password_temporary?: boolean;
  is_active?: boolean;
  is_superuser?: boolean;
  roles?: string[];
  section_permissions?: Record<string, SectionAccessLevel>;
  exp?: number;
  iat?: number;
}

export interface AuthState {
  token: string | null;
  user: UserClaims | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}


export const TESTED_PILOT_SECTIONS: PlatformSectionKey[] = [
  'platform_home',
  'site_dashboard',
  'overall_dashboard',
  'dispatch_analysis',
  'alerts',
  'reports',
  'erp_explorer',
];

export const getDefaultPermissions = (): Record<string, SectionAccessLevel> => {
  const defaults: Record<string, SectionAccessLevel> = {};
  PLATFORM_SECTIONS.forEach((s) => {
    if (TESTED_PILOT_SECTIONS.includes(s)) {
      defaults[s] = 'view';
    } else {
      defaults[s] = 'none';
    }
  });
  return defaults;
};
