import { formatDisplayDate } from '../../../utils/date';
import { usePermissions } from '../../../hooks/usePermissions';
import React, { useEffect, useState } from 'react';
import { RefreshCw, Trash2, AlertTriangle, X, FileText, User } from 'lucide-react';
import { IconCloudUpload } from '../../../components/icons/LinealColorIcons';
import {
  UploadZone,
  LivePipelineVisualization,
  PipelineStages,
  ImportStatusDrawer,
  VerificationPanel,
  KPICards,
  ImportTimeline,
  RecentImports,
  NotificationToast,
} from '../components';
import {
  useERPJobsStore,
  useERPStatisticsStore,
  useERPNotificationStore,
  useERPProgressStore,
  useERPUploadStore,
} from '../stores';
import { erpApiClient } from '../api';
import { ImportJobResponse } from '../types';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';

export const ERPImportWorkspacePage: React.FC = () => {
  const [selectedJob, setSelectedJob] = useState<ImportJobResponse | null>(null);
  const [showAuditDrawer, setShowAuditDrawer] = useState(false);
  const { canEdit } = usePermissions();
  const [showResetModal, setShowResetModal] = useState(false);
  const [resetting, setResetting] = useState(false);

  const fetchJobs = useERPJobsStore((s) => s.fetchJobs);
  const fetchStatistics = useERPStatisticsStore((s) => s.fetchStatistics);
  const fetchAuditLogs = useERPStatisticsStore((s) => s.fetchAuditLogs);
  const auditLogs = useERPStatisticsStore((s) => s.auditLogs);
  const stats = useERPStatisticsStore((s) => s.statistics);
  const [auditTab, setAuditTab] = useState<'all' | 'reset' | 'lifecycle'>('all');
  const addNotification = useERPNotificationStore((s) => s.addNotification);
  const disconnectSSE = useERPProgressStore((s) => s.disconnectSSE);
  const resetUpload = useERPUploadStore((s) => s.resetUpload);

  useEffect(() => {
    fetchJobs();
    fetchStatistics();
    fetchAuditLogs();
  }, [fetchJobs, fetchStatistics, fetchAuditLogs]);

  const handleRefresh = () => {
    fetchJobs();
    fetchStatistics();
    fetchAuditLogs();
  };

  const handleConfirmReset = async () => {
    setResetting(true);
    try {
      const summary = await erpApiClient.resetDemoData();
      disconnectSSE();
      resetUpload();
      setSelectedJob(null);
      await fetchJobs();
      await fetchStatistics();
      await fetchAuditLogs();
      setShowResetModal(false);
      addNotification(
        'success',
        'Demo data reset complete. ' + summary.total_records_deleted + ' records deleted across ' + Object.keys(summary.deleted_counts).length + ' tables.'
      );
    } catch (err: any) {
      addNotification('error', err.message || 'Demo data reset failed.');
    } finally {
      setResetting(false);
    }
  };

  return (
    <DashboardSyncProvider onRefreshNeeded={handleRefresh}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <IconCloudUpload className="w-7 h-7 shrink-0" />
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                {/* ERP Import Workspace */}
                Operational Data Ingestion Hub
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Operational Ingestion, Canonical Validation &amp; Real-Time Persistence Telemetry
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {canEdit('erp_import') && (
              <button
                type="button"
                onClick={() => setShowResetModal(true)}
                className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-colors bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100 shadow-xs"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Reset Demo Data
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                fetchAuditLogs();
                setShowAuditDrawer(true);
              }}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-colors bg-white border-slate-200 hover:bg-slate-50 text-slate-700 shadow-xs"
              title="View Security & Operational Activity Trail"
            >
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              Activity Trail
            </button>
            <button
              type="button"
              onClick={handleRefresh}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-colors bg-white border-slate-200 hover:bg-slate-50 text-slate-700 shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Telemetry
            </button>
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Operational Reset Banner */}
        {stats?.is_reset_active && (
          <div className="p-4 rounded-lg border border-amber-300 bg-amber-50/90 text-amber-950 flex items-start gap-3 shadow-xs">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold uppercase tracking-wide text-amber-950">
                  Operational Data Reset Active
                </h4>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900 border border-amber-300">
                  Zero Live Records
                </span>
              </div>
              <p className="text-xs text-amber-900 font-medium">
                Operational tables (dispatches, trips, tickets, etc.) have been cleared. All prior imports are archived below. Any re-uploaded file (including <code className="bg-amber-100 px-1 py-0.5 rounded text-amber-950 font-bold border border-amber-300">05. T1 Mar-Apr 26.xlsx</code>) will receive a brand-new unique job number and will establish a fresh active operational dataset.
              </p>
            </div>
          </div>
        )}

        {/* Real-time KPI Cards */}
        <KPICards />

        {/* Primary Workspace Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Upload & Live Streaming */}
          <div className="lg:col-span-2 space-y-6">
            <UploadZone />
            <LivePipelineVisualization />
            <PipelineStages />
            <RecentImports onSelectJob={(job) => setSelectedJob(job)} />
          </div>

          {/* Right Column: Verification & Timeline */}
          <div className="space-y-6">
            <VerificationPanel />
            <ImportTimeline />
          </div>
        </div>

        {/* Admin Reset Modal */}
        {showResetModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-white border border-slate-200/90 rounded-lg p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2 font-bold text-rose-700 text-sm">
                  <AlertTriangle className="w-5 h-5" />
                  <span>Confirm Admin Reset</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowResetModal(false)}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3 text-xs text-slate-600">
                <p className="font-bold text-slate-900">
                  Are you sure you want to reset all ERP demo data?
                </p>
                <p className="font-medium">
                  This action executes inside a single PostgreSQL transaction to permanently delete:
                </p>
                <ul className="list-disc pl-5 space-y-1 font-medium text-slate-600">
                  <li>All Import Jobs &amp; Workbook Storage files</li>
                  <li>All Ingestion Entities (Plants, Sites, Customers, Vehicles, Drivers, Orders, Tickets, Dispatches, Invoices, Trips)</li>
                  <li>Audit Logs, Events, Checkpoints &amp; Statistics</li>
                </ul>
                <p className="p-3 rounded-lg border font-medium bg-amber-50 border-amber-200 text-amber-800">
                  Platform authentication, user claims, and core system settings will be preserved.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowResetModal(false)}
                  className="px-3.5 py-1.5 rounded-md border text-xs font-bold bg-white border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={resetting}
                  onClick={handleConfirmReset}
                  className="px-3.5 py-1.5 rounded-md text-white text-xs font-bold shadow-xs bg-rose-600 hover:bg-rose-700 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                >
                  {resetting ? 'Resetting Data...' : 'Confirm Transactional Reset'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Status Drawer Overlay */}
        <ImportStatusDrawer job={selectedJob} onClose={() => setSelectedJob(null)} />

        {/* Activity Trail Drawer */}
        {showAuditDrawer && (
          <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-white border-l border-slate-200/90 shadow-2xl p-6 z-50 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-600" />
                    Activity &amp; Audit Trail
                  </h2>
                  <p className="text-xs text-slate-500">Chronological history of file imports, deduplication &amp; resets</p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowAuditDrawer(false)}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Drawer Filter Tabs */}
              <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-sans">
                <button
                  type="button"
                  onClick={() => setAuditTab('all')}
                  className={`flex-1 py-1 px-2 rounded-md font-bold text-center transition-all ${
                    auditTab === 'all'
                      ? 'bg-white text-blue-800 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  All Logs ({auditLogs.length})
                </button>
                <button
                  type="button"
                  onClick={() => setAuditTab('reset')}
                  className={`flex-1 py-1 px-2 rounded-md font-bold text-center transition-all ${
                    auditTab === 'reset'
                      ? 'bg-white text-amber-800 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Reset & Revert ({auditLogs.filter((l) => l.action === 'DATA_RESET' || l.action === 'DATASET_REVERT').length})
                </button>
                <button
                  type="button"
                  onClick={() => setAuditTab('lifecycle')}
                  className={`flex-1 py-1 px-2 rounded-md font-bold text-center transition-all ${
                    auditTab === 'lifecycle'
                      ? 'bg-white text-emerald-800 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Ingestions ({auditLogs.filter((l) => l.action !== 'DATA_RESET' && l.action !== 'DATASET_REVERT').length})
                </button>
              </div>

              <div className="space-y-3">
                {auditLogs.filter((log) => {
                  if (auditTab === 'reset') return log.action === 'DATA_RESET' || log.action === 'DATASET_REVERT';
                  if (auditTab === 'lifecycle') return log.action !== 'DATA_RESET' && log.action !== 'DATASET_REVERT';
                  return true;
                }).length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No {auditTab === 'reset' ? 'reset events' : auditTab === 'lifecycle' ? 'ingestion events' : 'activity logs'} recorded yet.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100 border border-slate-200 rounded-md overflow-hidden bg-white">
                    {auditLogs
                      .filter((log) => {
                        if (auditTab === 'reset') return log.action === 'DATA_RESET' || log.action === 'DATASET_REVERT';
                        if (auditTab === 'lifecycle') return log.action !== 'DATA_RESET' && log.action !== 'DATASET_REVERT';
                        return true;
                      })
                      .map((log) => {
                      const uploader = (log.details?.uploaded_by && log.details.uploaded_by !== 'Sanjana Mahajan' ? log.details.uploaded_by : null) || log.details?.reverted_by || log.details?.reset_by || 'admin';
                      const isCompleted = log.action === 'JOB_COMPLETED';
                      const isCreated = log.action === 'JOB_CREATED';
                      const isReset = log.action === 'DATA_RESET';
                      const isRevert = log.action === 'DATASET_REVERT';
                      return (
                        <div key={log.id} className="p-3 text-xs hover:bg-slate-50/60 transition-colors">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                                isCompleted
                                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                                  : isReset
                                  ? 'bg-rose-50 border-rose-200 text-rose-700'
                                  : isRevert
                                  ? 'bg-amber-50 border-amber-300 text-amber-800'
                                  : isCreated
                                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                                  : 'bg-slate-100 border-slate-200 text-slate-700'
                              }`}
                            >
                              {log.action}
                            </span>
                            <span className="text-[11px] font-mono text-slate-400">
                              {formatDisplayDate(log.created_at)} {new Date(log.created_at).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 text-slate-600 font-medium mb-1">
                            <User className="w-3 h-3 text-slate-400 shrink-0" />
                            <span className="font-semibold text-slate-800">{uploader}</span>
                          </div>
                          {log.details && (
                            <div className="text-[11px] font-mono text-slate-500 bg-slate-50 p-2 rounded border border-slate-100 space-y-0.5 mt-1.5">
                              {log.details.file_name && <div>File: <span className="font-bold text-slate-700">{log.details.file_name}</span></div>}
                              {log.details.dataset_period && <div>Target Period: <span className="font-bold text-amber-800">{log.details.dataset_period}</span></div>}
                              {log.details.total_persisted !== undefined && (
                                <div className="text-slate-700">
                                  Persisted: <span className="font-bold">{log.details.total_persisted}</span> ({log.details.inserted_count ?? 0} new, {log.details.updated_count ?? 0} updated)
                                </div>
                              )}
                              {log.details.duration_seconds !== undefined && (
                                <div>Duration: <span className="font-bold">{log.details.duration_seconds}s</span></div>
                              )}
                              {log.details.reason && <div>Note: {log.details.reason}</div>}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex justify-end">
              <button
                type="button"
                onClick={() => setShowAuditDrawer(false)}
                className="px-4 py-2 rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 text-xs font-bold transition-colors"
              >
                Close Trail
              </button>
            </div>
          </div>
        )}

        {/* Global Toast Notifications */}
        <NotificationToast />
      </div>
    </DashboardSyncProvider>
  );
};

export default ERPImportWorkspacePage;
