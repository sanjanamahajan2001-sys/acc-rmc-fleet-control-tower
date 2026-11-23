import React, { useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { IconFileAuditSearch } from '../../../../components/icons/LinealColorIcons';
import { IntegrityDashboard } from '../components/IntegrityDashboard';
import { ExplorerGrid } from '../components/ExplorerGrid';
import { EntityDetailDrawer } from '../components/EntityDetailDrawer';
import { useERPExplorerStore } from '../stores';
import { useERPStatisticsStore } from '../../stores';
import { SyncStatusHeaderBadge } from '../../../site_dashboard/components/SyncStatusHeaderBadge';
import { DashboardSyncProvider } from '../../../site_dashboard/orchestration/DashboardSyncProvider';

export const ERPExplorerPage: React.FC = () => {
  const { fetchEntityData, fetchImportHistory, fetchAuditLogs } = useERPExplorerStore();
  const fetchStatistics = useERPStatisticsStore((s) => s.fetchStatistics);

  useEffect(() => {
    fetchEntityData();
    fetchImportHistory();
    fetchAuditLogs();
    fetchStatistics();
  }, [fetchEntityData, fetchImportHistory, fetchAuditLogs, fetchStatistics]);

  const handleRefresh = () => {
    fetchEntityData();
    fetchImportHistory();
    fetchAuditLogs();
    fetchStatistics();
  };

  return (
    <DashboardSyncProvider onRefreshNeeded={handleRefresh}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <IconFileAuditSearch className="w-7 h-7 shrink-0" />
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                ERP Data Explorer &amp; Audit Center
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Canonical Entity Inspection, Lineage Tracing &amp; Database Integrity Verification
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={handleRefresh}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-colors bg-white border-slate-200 hover:bg-slate-50 text-slate-700 shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Explorer Data
            </button>
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Feature 6 — Database Integrity Dashboard */}
        <IntegrityDashboard />

        {/* Feature 1 — Enterprise Explorer Grid */}
        <ExplorerGrid />

        {/* Feature 2 — Right-side Entity Inspection Drawer */}
        <EntityDetailDrawer />
      </div>
    </DashboardSyncProvider>
  );
};

export default ERPExplorerPage;
