import { useAuthStore } from '../store/auth';
import {
  PlatformSectionKey,
  SectionAccessLevel,
  PLATFORM_SECTIONS,
  getDefaultPermissions,
} from '../types/auth';

export interface UsePermissionsResult {
  canAccess: (section: PlatformSectionKey, requiredLevel?: SectionAccessLevel) => boolean;
  canEdit: (section: PlatformSectionKey) => boolean;
  canView: (section: PlatformSectionKey) => boolean;
  isSuperuser: boolean;
  isRestricted: boolean;
  permissions: Record<string, SectionAccessLevel>;
  activeSectionsCount: { view: number; edit: number };
}

export function usePermissions(): UsePermissionsResult {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);

  const isSuperuser = Boolean(
    user?.is_superuser ||
    (user?.roles && (user.roles.includes('Administrator') || user.roles.includes('admin')))
  );

  const permissions: Record<string, SectionAccessLevel> = (() => {
    if (isSuperuser) return {};
    if (user?.section_permissions && Object.keys(user.section_permissions).length > 0) {
      return user.section_permissions;
    }
    // Hydration guard: If token exists but user object is not yet loaded, default to operational view
    if (!user && token) {
      return getDefaultPermissions();
    }
    return getDefaultPermissions();
  })();

  const canAccess = (
    section: PlatformSectionKey,
    requiredLevel: SectionAccessLevel = 'view'
  ): boolean => {
    if (isSuperuser) return true;

    // If completely unauthenticated
    if (!user && !token) return false;

    // During hydration before user claims are loaded, permit basic viewing of operational items
    if (!user && token) {
      if (section === 'settings' || section === 'user_management' || section === 'erp_import') {
        return false;
      }
      return requiredLevel === 'view';
    }

    const userLevel = permissions[section] || 'none';
    if (userLevel === 'none') return false;

    if (requiredLevel === 'none') return true;
    if (requiredLevel === 'view') {
      return userLevel === 'view' || userLevel === 'edit';
    }
    if (requiredLevel === 'edit') {
      return userLevel === 'edit';
    }
    return false;
  };

  const canView = (section: PlatformSectionKey) => canAccess(section, 'view');
  const canEdit = (section: PlatformSectionKey) => canAccess(section, 'edit');

  const activeSectionsCount = (() => {
    if (isSuperuser) return { view: 14, edit: 14 };
    const vals = Object.values(permissions);
    return {
      edit: vals.filter((v) => v === 'edit').length,
      view: vals.filter((v) => v === 'view').length,
    };
  })();

  // ONLY mark restricted if user is authenticated, loaded, NOT superuser, and has fewer than 14 edit rights
  const isRestricted = Boolean(user && !isSuperuser && activeSectionsCount.edit < 14);

  return {
    canAccess,
    canEdit,
    canView,
    isSuperuser,
    isRestricted,
    permissions,
    activeSectionsCount,
  };
}
