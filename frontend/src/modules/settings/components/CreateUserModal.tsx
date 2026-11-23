import { env } from '../../../config/env';
import React, { useState } from 'react';
import { X, Copy, Check, AlertCircle } from 'lucide-react';
import { IconUserGroup, IconShieldSecure } from '../../../components/icons/LinealColorIcons';
import { PermissionMatrixTable } from './PermissionMatrixTable';
import { SectionAccessLevel, PLATFORM_SECTIONS } from '../../../types/auth';

interface RoleOption {
  id: string;
  name: string;
}

interface PlantOption {
  id: string;
  code?: string;
  name: string;
}

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  token: string | null;
  availableRoles: RoleOption[];
  availablePlants: PlantOption[];
}

export const CreateUserModal: React.FC<CreateUserModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  token,
  availableRoles,
}) => {
  const getDefaultPermissions = (): Record<string, SectionAccessLevel> => {
    const demo: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      if (s === 'settings' || s === 'user_management' || s === 'erp_import') {
        demo[s] = 'none';
      } else {
        demo[s] = 'view';
      }
    });
    return demo;
  };

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [selectedPlantIds] = useState<string[]>([]);
  // Legacy Role State (Preserved as commented-out reference)
  // const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  // const handleRoleToggle = (roleId: string) => {
  //   setSelectedRoleIds((prev) =>
  //     prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId]
  //   );
  // };
  const [sectionPermissions, setSectionPermissions] = useState<Record<string, SectionAccessLevel>>(getDefaultPermissions);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // One-time temporary password state
  const [createdTempPassword, setCreatedTempPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const isFullAdmin = PLATFORM_SECTIONS.every((s) => (sectionPermissions[s] || 'none') === 'edit');
      const targetRoles = isFullAdmin ? ['Administrator'] : ['Operator'];

      const response = await fetch(env.VITE_API_BASE_URL + '/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token,
        },
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          full_name: fullName.trim() || null,
          role_ids: targetRoles,
          plant_ids: selectedPlantIds,
          section_permissions: sectionPermissions,
        }),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error?.message || result.detail || 'Failed to create user');
      }

      setCreatedTempPassword(result.data.temporary_password);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Error creating user');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyPassword = () => {
    if (createdTempPassword) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(createdTempPassword);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = createdTempPassword;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCloseDialog = () => {
    setCreatedTempPassword(null);
    setUsername('');
    setEmail('');
    setFullName('');
    // setSelectedRoleIds([]); // Legacy role state reset
    setSectionPermissions(getDefaultPermissions());
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="max-w-4xl w-full bg-white border border-slate-200/90 rounded-lg p-6 shadow-2xl space-y-4 relative text-slate-800 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <IconUserGroup className="w-6 h-6 shrink-0" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Create New Platform User</h2>
              <p className="text-[11px] text-slate-500 font-medium">Provision user details, assigned roles, and plant scope</p>
            </div>
          </div>
          <button onClick={handleCloseDialog} className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-2.5 rounded-md bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {/* Display One-Time Temporary Password after Creation */}
        {createdTempPassword ? (
          <div className="space-y-3.5 py-1">
            <div className="p-3.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs space-y-1">
              <div className="flex items-center gap-2 font-bold text-emerald-700 text-sm">
                <IconShieldSecure className="w-4 h-4" />
                <span>User Created Successfully!</span>
              </div>
              <p className="text-slate-600 text-xs">
                A one-time temporary password has been generated. Provide these credentials to the user.
              </p>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                One-Time Temporary Password
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={createdTempPassword}
                  className="flex-1 py-2 px-3 rounded-md bg-slate-50 border border-slate-200 font-mono text-xs text-amber-800 font-bold select-all focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleCopyPassword}
                  className="py-2 px-3.5 rounded-md bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold flex items-center gap-1.5 transition-colors shadow-xs"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <div className="p-2.5 rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-[11px]">
              ⚠️ <strong>Security Notice:</strong> This temporary password will NOT be retrievable again after closing. The user will be required to update it on first login.
            </div>

            <button
              onClick={handleCloseDialog}
              className="w-full py-2 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold transition-colors shadow-xs"
            >
              Done &amp; Close Dialog
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                  Username *
                </label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. jdoe"
                  className="w-full px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600"
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                  Email Address *
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jdoe@fleetcontrol.io"
                  className="w-full px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="w-full px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600"
              />
            </div>

            {/* Legacy Role Selection (Preserved as commented-out reference) */}
            {/*
            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider block text-[11px]">
                Assign Roles
              </label>
              <div className="flex flex-wrap gap-1.5 p-2 rounded-md bg-slate-50 border border-slate-200 max-h-24 overflow-y-auto">
                {availableRoles.map((role) => {
                  const active = selectedRoleIds.includes(role.id) || selectedRoleIds.includes(role.name);
                  return (
                    <button
                      key={role.id}
                      type="button"
                      onClick={() => handleRoleToggle(role.id)}
                      className={`px-2.5 py-1 rounded border font-bold transition-colors text-[11px] ${
                        active
                          ? 'bg-blue-700 border-blue-700 text-white shadow-2xs'
                          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {role.name}
                    </button>
                  );
                })}
              </div>
            </div>
            */}

            {/* Section-Based Permission Matrix */}
            <PermissionMatrixTable
              permissions={sectionPermissions}
              onChange={setSectionPermissions}
            />

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={handleCloseDialog}
                className="py-1.5 px-3.5 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold transition-colors shadow-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="py-1.5 px-4 rounded-md bg-blue-700 hover:bg-blue-800 text-white font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-xs"
              >
                {loading ? 'Provisioning User...' : 'Create & Generate Temp Credential'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
