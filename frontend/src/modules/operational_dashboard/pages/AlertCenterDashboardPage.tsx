import React from 'react';
import { IconAlertBell } from '../../../components/icons/LinealColorIcons';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { DashboardFilterProvider } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { useOperationalDashboardContext } from '../hooks/useOperationalDashboardContext';
import { AlertCenterWorkspaceContent } from '../widgets/alerts/AlertCenterWorkspaceContent';

const AlertCenterDashboardContent: React.FC = () => {
  const { refetchContext } = useOperationalDashboardContext();

  return (
    <DashboardSyncProvider onRefreshNeeded={refetchContext}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Top Header Bar for Operational Alert Center */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconAlertBell className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Operational Alert Center
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Real-Time Business Rule Exceptions &amp; SLA Management
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Dashboard Filter Bar (Shared filter provider contract) */}
        <GlobalDashboardFilterBar />

        {/* Primary Workspace Content Area: Alert Center Content ONLY */}
        <div className="w-full">
          <AlertCenterWorkspaceContent />
        </div>
      </div>
    </DashboardSyncProvider>
  );
};

export const AlertCenterDashboardPage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <AlertCenterDashboardContent />
    </DashboardFilterProvider>
  );
};

export default AlertCenterDashboardPage;
