import { formatDisplayDateTime } from '../../../utils/date';
import { env } from '../../../config/env';
import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../../store/auth';
import { CreateUserModal } from '../components/CreateUserModal';
import { EditUserModal } from '../components/EditUserModal';
import { ResetPasswordModal } from '../components/ResetPasswordModal';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import {
  UserX,
  Search,
  UserPlus,
  Edit2,
  RefreshCw,
  Trash2,
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react';
import { IconUserGroup, IconCalendarCheckmark, IconShieldSecure, IconKeySecurity } from '../../../components/icons/LinealColorIcons';

interface PlantScope {
  id: string;
  code: string;
  name: string;
}

interface UserDetail {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  auth_stage: string;
  is_password_temporary: boolean;
  password_changed_at: string | null;
  deleted_at: string | null;
  deleted_by: string | null;
  roles: string[];
  section_permissions?: Record<string, 'none' | 'view' | 'edit'>;
  plant_scopes: PlantScope[];
  last_login_at: string | null;
}

export const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<UserDetail[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserDetail | null>(null);
  const [resetUser, setResetUser] = useState<{ id: string; username: string } | null>(null);
  const [deactivatingUser, setDeactivatingUser] = useState<UserDetail | null>(null);

  const token = useAuthStore((state) => state.token);

  // Hardcoded canonical roles and plants for options
  const availableRoles = [
    { id: 'Administrator', name: 'Administrator' },
    { id: 'Plant Dispatcher', name: 'Plant Dispatcher' },
    { id: 'Fleet Supervisor', name: 'Fleet Supervisor' },
    { id: 'Executive Viewer', name: 'Executive Viewer' },
  ];

  const availablePlants = [
    { id: 'P-101', code: 'P-101', name: 'Central Batching Plant 1' },
    { id: 'P-102', code: 'P-102', name: 'North ReadyMix Depot' },
    { id: 'P-103', code: 'P-103', name: 'South Transit Yard' },
  ];

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      let url = env.VITE_API_BASE_URL + '/users?page=' + page + '&size=' + pageSize;
      if (search) url += '&search=' + encodeURIComponent(search);
      if (statusFilter === 'ACTIVE') url += '&is_active=true';
      if (statusFilter === 'DISABLED') url += '&is_active=false';
      if (statusFilter === 'PASSWORD_CHANGE') url += '&must_change_password=true';
      if (roleFilter !== 'ALL') url += '&role=' + encodeURIComponent(roleFilter);

      const response = await fetch(url, {
        headers: { Authorization: 'Bearer ' + token },
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access Denied: You must be an Administrator to access user governance.');
        }
        throw new Error('Failed to retrieve user accounts from server.');
      }

      const result = await response.json();
      if (result.success && result.data) {
        setUsers(result.data.items || []);
        setTotalUsers(result.data.total || 0);
        setTotalPages(result.data.pages || 1);
      }
    } catch (err: any) {
      setError(err.message || 'Error fetching user directory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, statusFilter, roleFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleDeactivate = async () => {
    if (!deactivatingUser) return;

    try {
      const response = await fetch(env.VITE_API_BASE_URL + '/users/' + deactivatingUser.id, {
        method: 'DELETE',
        headers: { Authorization: 'Bearer ' + token },
      });

      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.error?.message || 'Error deactivating user');
      }

      setDeactivatingUser(null);
      fetchUsers();
    } catch (err: any) {
      alert(err.message || 'Error deactivating user');
    }
  };

  // Metrics derivation
  const activeCount = users.filter((u) => u.is_active).length;
  const adminCount = users.filter((u) => u.is_superuser || u.roles.includes('Administrator')).length;
  const passwordChangeReqCount = users.filter((u) => u.must_change_password).length;

  // Derivation for permission matrix badge
  const getPermissionBadge = (u: UserDetail) => {
    if (u.is_superuser) {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded border border-purple-200 bg-purple-50 text-purple-700 text-[10px] font-bold">
          Full Access (Superuser)
        </span>
      );
    }
    const perms = u.section_permissions || {};
    const entries = Object.values(perms);
    const editCount = entries.filter((l) => l === 'edit').length;
    const viewCount = entries.filter((l) => l === 'view').length;

    if (editCount >= 14) {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded border border-indigo-200 bg-indigo-50 text-indigo-700 text-[10px] font-bold">
          Full Access (14/14)
        </span>
      );
    }
    if (editCount === 0 && viewCount === 0) {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-500 text-[10px] font-medium">
          Default Role Access
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded border border-blue-200 bg-blue-50 text-blue-700 text-[10px] font-bold">
        {editCount > 0 ? `${editCount} Edit` : ''}
        {editCount > 0 && viewCount > 0 ? ', ' : ''}
        {viewCount > 0 ? `${viewCount} View` : ''}
      </span>
    );
  };

  return (
    <DashboardSyncProvider onRefreshNeeded={fetchUsers}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <IconUserGroup className="w-7 h-7 shrink-0" />
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                User Management &amp; Administrative Governance
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Manage platform user accounts, assign role permissions, and control operational plant authorization
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsCreateOpen(true)}
              className="py-1.5 px-3.5 rounded-md bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-colors"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Create New User</span>
            </button>
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* KPI Ribbon */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg border border-slate-200/90 bg-white flex items-center gap-3 shadow-xs">
            <IconUserGroup className="w-7 h-7 shrink-0" />
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total Users (Page)</p>
              <h3 className="text-xl font-bold font-mono text-slate-900">{users.length}</h3>
            </div>
          </div>

          <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center gap-3 shadow-xs">
            <IconCalendarCheckmark className="w-7 h-7 shrink-0" />
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">Active Users (Page)</p>
              <h3 className="text-xl font-bold font-mono text-emerald-700">{activeCount}</h3>
            </div>
          </div>

          <div className="p-4 rounded-lg border border-slate-200/90 bg-white flex items-center gap-3 shadow-xs">
            <IconShieldSecure className="w-7 h-7 shrink-0" />
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Administrators (Page)</p>
              <h3 className="text-xl font-bold font-mono text-slate-900">{adminCount}</h3>
            </div>
          </div>

          <div className="p-4 rounded-lg border border-amber-200 bg-amber-50/50 flex items-center gap-3 shadow-xs">
            <IconKeySecurity className="w-7 h-7 shrink-0" />
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700">Password Pending (Page)</p>
              <h3 className="text-xl font-bold font-mono text-amber-700">{passwordChangeReqCount}</h3>
            </div>
          </div>
        </div>

        {/* Action Controls & Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-lg border border-slate-200/90 bg-white shadow-xs">
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-sm">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search username, email, full name..."
                className="w-full pl-8 pr-3 py-1.5 rounded-md border border-slate-200 text-xs font-medium focus:outline-none focus:border-blue-600 bg-white text-slate-800 placeholder:text-slate-400"
              />
            </div>
            <button
              type="submit"
              className="py-1.5 px-3 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 transition-colors shadow-xs"
            >
              Search
            </button>
          </form>

          <div className="flex flex-wrap items-center gap-2.5">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-md border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-blue-600"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Accounts</option>
              <option value="DISABLED">Disabled Accounts</option>
              <option value="PASSWORD_CHANGE">Password Change Required</option>
            </select>

            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-md border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-blue-600"
            >
              <option value="ALL">All Roles</option>
              <option value="Administrator">Administrator</option>
              <option value="Plant Dispatcher">Plant Dispatcher</option>
              <option value="Fleet Supervisor">Fleet Supervisor</option>
              <option value="Executive Viewer">Executive Viewer</option>
            </select>

            <button
              onClick={() => fetchUsers()}
              className="p-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-xs transition-colors"
              title="Refresh Users"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-3.5 rounded-lg border border-rose-200 bg-rose-50 text-xs font-bold text-rose-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              <span>{error}</span>
            </div>
            <button onClick={() => fetchUsers()} className="underline font-bold text-rose-700">
              Retry
            </button>
          </div>
        )}

        {/* Users Data Table */}
        <div className="rounded-lg border border-slate-200/90 bg-white overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 uppercase tracking-wider text-[10px] font-bold text-slate-500">
                  <th className="py-2.5 px-3.5">User Identity</th>
                  <th className="py-2.5 px-3.5">Permissions & Roles</th>
                  <th className="py-2.5 px-3.5">Account Status</th>
                  <th className="py-2.5 px-3.5">Password Stage</th>
                  <th className="py-2.5 px-3.5">Last Login</th>
                  <th className="py-2.5 px-3.5 text-right font-sans">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center font-bold text-slate-500 font-sans">
                      Loading user directory from server...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center font-medium text-slate-500 font-sans">
                      No user accounts found matching current query.
                    </td>
                  </tr>
                ) : (
                  users.map((u, idx) => (
                    <tr key={u.id} className={`hover:bg-slate-50/80 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                      <td className="py-2.5 px-3.5">
                        <div className="font-bold text-xs text-slate-900 font-sans">{u.username}</div>
                        <div className="text-[11px] font-medium text-slate-500">{u.email}</div>
                        {u.full_name && <div className="text-[10px] font-medium text-slate-600 font-sans">{u.full_name}</div>}
                      </td>

                      <td className="py-2.5 px-3.5">
                        <div className="flex flex-col gap-1.5">
                          <div>{getPermissionBadge(u)}</div>
                          <div className="flex flex-wrap gap-1">
                            {u.is_superuser && (
                              <span className="px-1.5 py-0.5 rounded border border-blue-200 bg-blue-50 text-blue-700 text-[10px] font-bold">
                                Superuser
                              </span>
                            )}
                            {u.roles.map((r) => (
                              <span key={r} className="px-1.5 py-0.5 rounded border border-slate-200 bg-slate-100 text-slate-700 text-[10px] font-bold font-sans">
                                {r}
                              </span>
                            ))}
                          </div>
                        </div>
                      </td>

                      <td className="py-2.5 px-3.5 font-sans">
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                            <CheckCircle2 className="w-3 h-3" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-rose-200 bg-rose-50 text-rose-700 font-bold text-[10px]">
                            <UserX className="w-3 h-3" /> Disabled
                          </span>
                        )}
                      </td>

                      <td className="py-2.5 px-3.5 font-sans">
                        {u.must_change_password ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-amber-200 bg-amber-50 text-amber-700 font-bold text-[10px]">
                            <IconKeySecurity className="w-3.5 h-3.5 inline-block" /> Temp / Pending Change
                          </span>
                        ) : (
                          <span className="text-[11px] font-medium text-slate-500">Normal</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3.5 font-medium text-[11px] text-slate-500">
                        {u.last_login_at ? formatDisplayDateTime(u.last_login_at) : 'Never'}
                      </td>

                      <td className="py-2.5 px-3.5 text-right font-sans">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setEditingUser(u)}
                            title="Edit User Details"
                            className="p-1 rounded border border-slate-200 bg-white text-blue-700 hover:bg-blue-50 transition-colors shadow-2xs"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => setResetUser({ id: u.id, username: u.username })}
                            title="Reset Password"
                            className="p-1 rounded border border-slate-200 bg-white text-amber-700 hover:bg-amber-50 transition-colors shadow-2xs"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => setDeactivatingUser(u)}
                            title="Deactivate Account"
                            className="p-1 rounded border border-slate-200 bg-white text-rose-700 hover:bg-rose-50 transition-colors shadow-2xs"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-3 bg-slate-50/50 border-t border-slate-200 flex items-center justify-between text-xs font-mono font-medium text-slate-500">
            <span>
              Showing Page <strong className="text-slate-900 font-bold">{page}</strong> of <strong className="text-slate-900 font-bold">{totalPages}</strong> ({totalUsers} total users)
            </span>

            <div className="flex items-center gap-1.5 font-sans">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-40 transition-colors shadow-2xs"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="p-1.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-40 transition-colors shadow-2xs"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Modals */}
        <CreateUserModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onSuccess={fetchUsers}
          token={token}
          availableRoles={availableRoles}
          availablePlants={availablePlants}
        />

        <EditUserModal
          isOpen={Boolean(editingUser)}
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSuccess={fetchUsers}
          token={token}
          availableRoles={availableRoles}
          availablePlants={availablePlants}
        />

        <ResetPasswordModal
          isOpen={Boolean(resetUser)}
          userId={resetUser?.id || null}
          username={resetUser?.username || null}
          onClose={() => setResetUser(null)}
          onSuccess={fetchUsers}
          token={token}
        />

        {/* Deactivation Confirmation Modal */}
        {deactivatingUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <div className="max-w-md w-full bg-white border border-slate-200/90 rounded-lg p-6 shadow-2xl space-y-4 text-slate-800">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2 text-rose-700 font-bold text-sm">
                  <Trash2 className="w-4 h-4" />
                  <span>Confirm Soft Deactivation</span>
                </div>
                <button
                  onClick={() => setDeactivatingUser(null)}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-xs text-slate-600">
                Are you sure you want to deactivate the user account for <strong className="text-slate-900">{deactivatingUser.username}</strong>?
                The account will be soft-deleted, active sessions will be invalidated, and login will be disabled.
              </p>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100 text-xs">
                <button
                  onClick={() => setDeactivatingUser(null)}
                  className="py-1.5 px-3.5 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold transition-colors shadow-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeactivate}
                  className="py-1.5 px-4 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-bold transition-colors shadow-xs"
                >
                  Deactivate Account
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardSyncProvider>
  );
};

export default UserManagementPage;
