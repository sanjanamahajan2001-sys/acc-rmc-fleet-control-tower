import { usePermissions } from '../../../hooks/usePermissions';
import { env } from '../../../config/env';
import React, { useState, useEffect } from 'react';
import { DatabasePreviewSection } from './DatabasePreviewSection';
import { Database, Layers } from 'lucide-react';
import { useAuthStore } from '../../../store/auth';

import { IconBatchingPlantFactory, IconShieldSecure } from '../../../components/icons/LinealColorIcons';
import {
  Search,
  Edit2,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Save,
  X,
  Info,
  HelpCircle,
} from 'lucide-react';

export interface PlantContext {
  id: string;
  code: string;
  name: string;
}

export interface CustomerSettingsItem {
  id: string;
  code: string;
  raw_customer_name: string;
  effective_customer_name: string;
  override_name: string | null;
  override_reason: string | null;
  updated_at: string | null;
  updated_by_name: string | null;
  is_overridden: boolean;
  plants: PlantContext[];
}

export const CompanyCustomerSettingsSection: React.FC = () => {
  const [customers, setCustomers] = useState<CustomerSettingsItem[]>([]);
  const [totalCustomers, setTotalCustomers] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'customers' | 'database'>('customers');

  // Edit State
  const [editingItem, setEditingItem] = useState<CustomerSettingsItem | null>(null);
  const [editInputName, setEditInputName] = useState('');
  const [editReason, setEditReason] = useState('');
  const [showSaveConfirmModal, setShowSaveConfirmModal] = useState(false);
  const [saving, setSaving] = useState(false);

  // Reset State
  const [resetItem, setResetItem] = useState<CustomerSettingsItem | null>(null);
  const [resetting, setResetting] = useState(false);

  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);

  const { canEdit } = usePermissions();
  // Permissive check: user has edit access to settings section OR is superuser
  const isAdmin = canEdit('settings');


  const fetchCustomerSettings = async () => {
    setLoading(true);
    setError(null);

    try {
      let url = `${env.VITE_API_BASE_URL}/settings/customer-overrides?page=${page}&size=${pageSize}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;

      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = 'Bearer ' + token;
      }

      const response = await fetch(url, { headers });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('401 Unauthorized: Session expired or unauthenticated');
        }
        if (response.status === 403) {
          throw new Error('403 Forbidden: Administrative permission required');
        }
        throw new Error('Failed to load customer settings (HTTP ' + response.status + ')');
      }

      const resData = await response.json();
      const rawPayload = resData.data || resData;

      let rawItems: any[] = [];
      let total = 0;

      if (Array.isArray(rawPayload)) {
        rawItems = rawPayload;
        total = rawPayload.length;
      } else if (rawPayload && Array.isArray(rawPayload.items)) {
        rawItems = rawPayload.items;
        total = rawPayload.total || rawPayload.items.length;
      }

      const normalized: CustomerSettingsItem[] = rawItems.map((item: any) => ({
        id: item.customer_id || item.id,
        code: item.customer_code || item.code,
        raw_customer_name: item.raw_customer_name,
        effective_customer_name: item.effective_customer_name,
        override_name: item.override_name || (item.is_overridden ? item.effective_customer_name : null),
        override_reason: item.override_reason || null,
        updated_at: item.updated_at || null,
        updated_by_name: item.updated_by_name || null,
        is_overridden: Boolean(item.is_overridden),
        plants: (item.plants || []).map((p: any) => ({
          id: p.plant_id || p.id,
          code: p.plant_code || p.code,
          name: p.plant_name || p.name,
        })),
      }));

      setCustomers(normalized);
      setTotalCustomers(total);
      setTotalPages(Math.ceil(total / pageSize) || 1);
    } catch (err: any) {

      setError(err.message || 'An unexpected error occurred loading Customer settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomerSettings();
  }, [page, search]);

  const showToast = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification(null);
    }, 4000);
  };

  // --- Save Flow ---
  const handleOpenEdit = (item: CustomerSettingsItem) => {
    if (!isAdmin) return;
    setEditingItem(item);
    setEditInputName(item.effective_customer_name);
    setEditReason(item.override_reason || '');
  };

  const handleCloseEdit = () => {
    setEditingItem(null);
    setEditInputName('');
    setEditReason('');
    setShowSaveConfirmModal(false);
  };

  const handleInitiateSave = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = editInputName.trim();
    if (!trimmed) {
      showToast('error', 'Company/Customer Name cannot be empty or whitespace-only.');
      return;
    }
    if (trimmed.length > 255) {
      showToast('error', 'Company/Customer Name cannot exceed 255 characters.');
      return;
    }
    setShowSaveConfirmModal(true);
  };

  const handleConfirmSave = async () => {
    if (!editingItem) return;
    setSaving(true);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = 'Bearer ' + token;
      }

      const response = await fetch(env.VITE_API_BASE_URL + '/settings/customer-overrides/' + editingItem.id, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          override_name: editInputName.trim(),
          override_reason: editReason.trim() || undefined,
        }),
      });


      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || errorBody.message || ('Save failed (HTTP ' + response.status + ')'));
      }

      showToast('success', 'Display name updated to "' + editInputName.trim() + '"');
      handleCloseEdit();
      window.dispatchEvent(new CustomEvent('fleet-settings-updated'));
      window.dispatchEvent(new CustomEvent('customer-overrides-updated'));
      await fetchCustomerSettings(); // Refetch authoritative state from backend
    } catch (err: any) {
      showToast('error', err.message || 'Failed to update customer display override.');
    } finally {
      setSaving(false);
    }
  };

  // --- Reset Flow ---
  const handleInitiateReset = (item: CustomerSettingsItem) => {
    if (!isAdmin) return;
    setResetItem(item);
  };

  const handleConfirmReset = async () => {
    if (!resetItem) return;
    setResetting(true);

    try {
      const response = await fetch(env.VITE_API_BASE_URL + '/settings/customer-overrides/' + resetItem.id, {
        method: 'DELETE',
        headers: {
          Authorization: 'Bearer ' + token,
        },
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || errorBody.message || ('Reset failed (HTTP ' + response.status + ')'));
      }

      showToast('success', 'Reset customer display name to ERP canonical name "' + resetItem.raw_customer_name + '".');
      setResetItem(null);
      window.dispatchEvent(new CustomEvent('fleet-settings-updated'));
      window.dispatchEvent(new CustomEvent('customer-overrides-updated'));
      await fetchCustomerSettings(); // Refetch authoritative state from backend
    } catch (err: any) {
      showToast('error', err.message || 'Failed to reset customer display override.');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl border shadow-xs" style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}>
        <div className="flex items-center gap-3.5">
          <IconBatchingPlantFactory className="w-7 h-7 shrink-0" />
          <div>
            <h2 className="text-lg font-bold tracking-tight flex items-center gap-2" style={{ color: '#172033' }}>
              Company &amp; Customer Accounts
            </h2>
            <p className="text-xs font-medium mt-0.5" style={{ color: '#64748B' }}>
              Configure administrative display names for ERP-derived customer entities across Fleet Control Tower.
            </p>
          </div>
        </div>

        {/* Read-only Data Protection Alert Badge */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-bold" style={{ backgroundColor: '#FEF3C7', borderColor: '#FCD34D', color: '#B7791F' }}>
          <Info className="w-4 h-4 shrink-0" style={{ color: '#B7791F' }} />
          <span>Display/Configuration Layer (ERP Master Data is Immutably Preserved)</span>
        </div>
      </div>

      {/* Toast Notification */}
      {notification && (
        <div
          className="p-4 rounded-xl border text-xs font-bold flex items-center justify-between transition-all"
          style={
            notification.type === 'success'
              ? { backgroundColor: '#ECFDF5', borderColor: '#A7F3D0', color: '#16805C' }
              : { backgroundColor: '#FEF2F2', borderColor: '#FCA5A5', color: '#C83B4B' }
          }
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" style={{ color: '#16805C' }} />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" style={{ color: '#C83B4B' }} />
            )}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="hover:opacity-80">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Toolbar: Search + RBAC Banner */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by customer, code, or plant..."
            className="w-full pl-9 pr-4 py-2 rounded-xl border text-xs font-medium focus:outline-none min-h-[36px]"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA', color: '#172033' }}
          />
        </div>

        {!isAdmin && (
          <div className="flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-xl border" style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA', color: '#64748B' }}>
            <IconShieldSecure className="w-4 h-4" />
            <span>Read-Only View (Administrator rights required to edit display names)</span>
          </div>
        )}
      </div>

      {/* Table Container */}
      <div className="rounded-2xl border overflow-hidden shadow-xs" style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}>
        {loading ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-blue-700 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs font-bold" style={{ color: '#64748B' }}>Loading customer accounts...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center space-y-3">
            <AlertCircle className="w-8 h-8 mx-auto" style={{ color: '#C83B4B' }} />
            <p className="text-xs font-bold" style={{ color: '#C83B4B' }}>{error}</p>
            <button
              onClick={fetchCustomerSettings}
              className="px-3.5 py-1.5 rounded-xl border text-xs font-bold hover:bg-[#F4F6F9]"
              style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA', color: '#172033' }}
            >
              Retry
            </button>
          </div>
        ) : customers.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <IconBatchingPlantFactory className="w-8 h-8 mx-auto" />
            <p className="text-xs font-bold" style={{ color: '#172033' }}>No Customer Accounts Found</p>
            <p className="text-[11px] font-medium" style={{ color: '#64748B' }}>
              {search ? 'Try adjusting your search criteria.' : 'No customer records are currently ingested in the platform.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b uppercase font-bold text-[11px]" style={{ backgroundColor: '#F4F6F9', borderColor: '#DCE2EA', color: '#64748B' }}>
                  <th className="py-3 px-4">Plant Context (Read-Only)</th>
                  <th className="py-3 px-4">Customer Code</th>
                  <th className="py-3 px-4">ERP Customer Name (Read-Only)</th>
                  <th className="py-3 px-4">Company/Customer Display Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: '#DCE2EA', color: '#172033' }}>
                {customers.map((cust) => (
                  <tr key={cust.id} className="hover:bg-[#F4F6F9] transition-colors">
                    {/* Plant Context (Multi-Plant) */}
                    <td className="py-3.5 px-4 align-top">
                      {cust.plants && cust.plants.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5 max-w-xs">
                          {cust.plants.map((p) => (
                            <span
                              key={p.id}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[11px] font-bold"
                              style={{ backgroundColor: '#F4F6F9', borderColor: '#DCE2EA', color: '#172033' }}
                              title={'Plant Code: ' + p.code}
                            >
                              <IconBatchingPlantFactory className="w-3.5 h-3.5" />
                              {p.name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="italic text-[11px]" style={{ color: '#64748B' }}>Unassigned</span>
                      )}
                    </td>

                    {/* Customer Code */}
                    <td className="py-3.5 px-4 align-top font-mono font-bold" style={{ color: '#475569' }}>
                      {cust.code}
                    </td>

                    {/* Canonical ERP Customer Name */}
                    <td className="py-3.5 px-4 align-top">
                      <div className="space-y-0.5">
                        <span className="font-bold" style={{ color: '#172033' }}>{cust.raw_customer_name}</span>
                        <span className="block text-[10px] uppercase font-mono font-semibold" style={{ color: '#64748B' }}>Canonical ERP Source</span>
                      </div>
                    </td>

                    {/* Effective Company/Customer Display Name */}
                    <td className="py-3.5 px-4 align-top">
                      <div className="space-y-1">
                        <span className="font-bold text-xs" style={{ color: cust.is_overridden ? '#4F46C5' : '#172033' }}>
                          {cust.effective_customer_name}
                        </span>
                        {cust.is_overridden && cust.override_reason && (
                          <p className="text-[10px] italic block font-medium" style={{ color: '#64748B' }}>
                            Reason: "{cust.override_reason}"
                          </p>
                        )}
                      </div>
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4 align-top">
                      {cust.is_overridden ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[10px] font-bold tracking-wide uppercase" style={{ backgroundColor: '#EEF0FF', borderColor: '#C7D2FE', color: '#4F46C5' }}>
                          MANUALLY OVERRIDDEN
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[10px] font-bold tracking-wide uppercase" style={{ backgroundColor: '#F4F6F9', borderColor: '#DCE2EA', color: '#64748B' }}>
                          ERP DEFAULT
                        </span>
                      )}
                    </td>

                    {/* Action Controls */}
                    <td className="py-3.5 px-4 align-top text-right">
                      {isAdmin ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(cust)}
                            className="px-2.5 py-1.5 rounded-lg border font-bold text-[11px] flex items-center gap-1.5 transition hover:bg-[#EEF0FF]"
                            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA', color: '#4F46C5' }}
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                            Edit
                          </button>
                          {cust.is_overridden && (
                            <button
                              type="button"
                              onClick={() => handleInitiateReset(cust)}
                              className="px-2.5 py-1.5 rounded-lg border font-bold text-[11px] flex items-center gap-1.5 transition hover:bg-[#FEF3C7]"
                              style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA', color: '#B7791F' }}
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              Reset to ERP
                            </button>
                          )}
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">Read-Only</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>
              Showing {customers.length} of {totalCustomers} accounts
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Edit Modal Dialog */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-indigo-400" />
                Edit Company/Customer Name
              </h3>
              <button onClick={handleCloseEdit} className="text-slate-400 hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleInitiateSave} className="space-y-4 text-xs">
              {/* Read-Only Context Fields */}
              <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px]">
                <div>
                  <span className="block text-slate-500 uppercase tracking-tight font-semibold">Customer Code</span>
                  <span className="font-mono text-slate-200 font-bold">{editingItem.code}</span>
                </div>
                <div>
                  <span className="block text-slate-500 uppercase tracking-tight font-semibold">ERP Customer Name (Read-Only)</span>
                  <span className="text-slate-300 font-semibold">{editingItem.raw_customer_name}</span>
                </div>
                <div className="col-span-2">
                  <span className="block text-slate-500 uppercase tracking-tight font-semibold">Associated Plants</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {editingItem.plants && editingItem.plants.length > 0 ? (
                      editingItem.plants.map((p) => (
                        <span key={p.id} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {p.name} ({p.code})
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 italic">Unassigned</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Editable Field */}
              <div className="space-y-1.5">
                <label className="block text-slate-300 font-semibold">
                  Company/Customer Display Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={editInputName}
                  onChange={(e) => setEditInputName(e.target.value)}
                  maxLength={255}
                  required
                  placeholder="Enter custom display name..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-indigo-500 transition font-medium"
                />
                <p className="text-[10px] text-slate-400">
                  This modifies the effective display name used across Control Tower. Raw ERP data is untouched.
                </p>
              </div>

              {/* Optional Reason Field */}
              <div className="space-y-1.5">
                <label className="block text-slate-400 font-semibold">Reason for Override (Optional)</label>
                <input
                  type="text"
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  placeholder="e.g. Legal entity rename, branding update..."
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500 transition"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleCloseEdit}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-500/20"
                >
                  <Save className="w-3.5 h-3.5" />
                  Review & Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Save Confirmation Dialog Modal */}
      {showSaveConfirmModal && editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-indigo-400">
              <HelpCircle className="w-6 h-6 shrink-0" />
              <h3 className="text-sm font-bold text-slate-100">Confirm Display Name Change</h3>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
              <div>
                <span className="block text-[10px] text-slate-500 uppercase tracking-tight font-semibold">Current Display Name</span>
                <span className="text-slate-300 font-medium">{editingItem.effective_customer_name}</span>
              </div>
              <div className="pt-2 border-t border-slate-800">
                <span className="block text-[10px] text-indigo-400 uppercase tracking-tight font-semibold">New Display Name</span>
                <span className="text-indigo-300 font-bold text-sm">{editInputName.trim()}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px]">
              <p>
                This changes the display name used by the Fleet Control Tower. The ERP customer name will remain unchanged.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={saving}
                onClick={() => setShowSaveConfirmModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Back
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleConfirmSave}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-500/20 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Confirm & Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Dialog Modal */}
      {resetItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-400">
              <RotateCcw className="w-6 h-6 shrink-0" />
              <h3 className="text-sm font-bold text-slate-100">Reset to ERP Default Name</h3>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
              <div>
                <span className="block text-[10px] text-slate-500 uppercase tracking-tight font-semibold">Current Display Name</span>
                <span className="text-slate-300 font-medium">{resetItem.effective_customer_name}</span>
              </div>
              <div className="pt-2 border-t border-slate-800">
                <span className="block text-[10px] text-emerald-400 uppercase tracking-tight font-semibold">ERP Canonical Name (Target)</span>
                <span className="text-emerald-300 font-bold">{resetItem.raw_customer_name}</span>
              </div>
            </div>

            <p className="text-xs text-slate-400">
              Are you sure you want to remove the manual display override for this customer account?
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={resetting}
                onClick={() => setResetItem(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={resetting}
                onClick={handleConfirmReset}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-amber-500/20 disabled:opacity-50"
              >
                {resetting ? 'Resetting...' : 'Confirm Reset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
