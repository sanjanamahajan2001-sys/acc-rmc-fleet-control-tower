import { env } from '../../../config/env';
import React, { useState, useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';
import { IconUserGroup } from '../../../components/icons/LinealColorIcons';
import { PermissionMatrixTable } from './PermissionMatrixTable';
import {
  SectionAccessLevel,
  PLATFORM_SECTIONS,
  getDefaultPermissions,
} from '../../../types/auth';

interface RoleOption {
  id: string;
  name: string;
}

interface PlantOption {
  id: string;
  code?: string;
  name: string;
}

interface UserDetail {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser?: boolean;
  roles: string[];
  section_permissions?: Record<string, SectionAccessLevel>;
  plant_scopes: { id: string; code?: string; name: string }[];
}

interface EditUserModalProps {
  isOpen: boolean;
  user: UserDetail | null;
  onClose: () => void;
  onSuccess: () => void;
  token: string | null;
  availableRoles: RoleOption[];
  availablePlants: PlantOption[];
}

export const EditUserModal: React.FC<EditUserModalProps> = ({
  isOpen,
  user,
  onClose,
  onSuccess,
  token,
}) => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [selectedPlantIds, setSelectedPlantIds] = useState<string[]>([]);
  const [sectionPermissions, setSectionPermissions] = useState<Record<string, SectionAccessLevel>>(getDefaultPermissions);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEmail(user.email || '');
      setIsActive(user.is_active);
      setSelectedPlantIds((user.plant_scopes || []).map((p) => p.code).filter((c): c is string => Boolean(c)));

      if (user.section_permissions && Object.keys(user.section_permissions).length > 0) {
        setSectionPermissions(user.section_permissions);
      } else if (user.is_superuser) {
        const full: Record<string, SectionAccessLevel> = {};
        PLATFORM_SECTIONS.forEach((s) => {
          full[s] = 'edit';
        });
        setSectionPermissions(full);
      } else {
        setSectionPermissions(getDefaultPermissions());
      }
    }
  }, [user]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const isFullAdmin = Boolean(user.is_superuser) || PLATFORM_SECTIONS.every((s) => (sectionPermissions[s] || 'none') === 'edit');
      const targetRoles = isFullAdmin ? ['Administrator'] : ['Operator'];

      const response = await fetch(env.VITE_API_BASE_URL + '/users/' + user.id, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token,
        },
        body: JSON.stringify({
          full_name: fullName.trim() || null,
          email: email.trim(),
          is_active: isActive,
          role_ids: targetRoles,
          plant_ids: selectedPlantIds,
          section_permissions: sectionPermissions,
        }),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error?.message || result.detail || 'Failed to update user');
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error updating user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="max-w-4xl w-full bg-white border border-slate-200/90 rounded-lg p-6 shadow-2xl space-y-4 relative text-slate-800 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <IconUserGroup className="w-6 h-6 shrink-0" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Edit User Details & Permissions</h2>
              <p className="text-[11px] text-slate-500 font-medium">Update profile, account status, and section access levels</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-2.5 rounded-md bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                Username (Immutable)
              </label>
              <input
                type="text"
                disabled
                value={user.username}
                className="w-full px-3 py-1.5 rounded-md bg-slate-50 border border-slate-200 text-slate-500 cursor-not-allowed font-mono text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-800 focus:outline-none focus:border-blue-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-800 focus:outline-none focus:border-blue-600"
              />
            </div>

            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                Account Status
              </label>
              <select
                value={isActive ? 'true' : 'false'}
                onChange={(e) => setIsActive(e.target.value === 'true')}
                className="w-full px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-800 focus:outline-none focus:border-blue-600 font-semibold"
              >
                <option value="true">Active Account</option>
                <option value="false">Disabled / Locked</option>
              </select>
            </div>
          </div>

          {/* Section-Based Permission Matrix */}
          <PermissionMatrixTable
            permissions={sectionPermissions}
            onChange={setSectionPermissions}
            isSuperuser={Boolean(user.is_superuser)}
            disabled={loading}
          />

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="py-1.5 px-3.5 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold transition-colors shadow-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="py-1.5 px-4 rounded-md bg-blue-700 hover:bg-blue-800 text-white font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-xs"
            >
              {loading ? 'Saving Changes...' : 'Save & Invalidate Stale Sessions'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
