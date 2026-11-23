import React from 'react';
import { BarChart3 } from 'lucide-react';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { DashboardFilterProvider } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { useOperationalDashboardContext } from '../hooks/useOperationalDashboardContext';
import { SiteComparisonTableCard } from '../components/SiteComparisonTableCard';

const SiteComparisonDashboardContent: React.FC = () => {
  const { refetchContext } = useOperationalDashboardContext();

  return (
    <DashboardSyncProvider onRefreshNeeded={refetchContext}>
      <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-5 space-y-6">
        {/* Top Header Bar for Site Comparison & Benchmarking */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-sky-600/15 text-sky-400 border border-sky-500/30">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                Site Comparison &amp; Benchmarking Dashboard
              </h1>
              <p className="text-xs text-slate-400">
                Multi-site operational benchmarking across dispatches, volume, holding, retention, queue &amp; SLA accuracy
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Dashboard Filter Bar (Shared filter provider contract) */}
        <GlobalDashboardFilterBar />

        {/* Primary Workspace Content Area: WS-04 Site Comparison Content ONLY */}
        <div className="w-full">
          <SiteComparisonTableCard />
        </div>
      </div>
    </DashboardSyncProvider>
  );
};

export const SiteComparisonDashboardPage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <SiteComparisonDashboardContent />
    </DashboardFilterProvider>
  );
};

export default SiteComparisonDashboardPage;
