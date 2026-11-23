import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { IconPlantSiteDashboard } from '../../../components/icons/LinealColorIcons';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { DashboardFilterProvider } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { useOperationalDashboardContext } from '../hooks/useOperationalDashboardContext';
import { ExecutiveKPIRibbon } from '../components/ExecutiveKPIRibbon';

interface OperationalDashboardShellContentProps {
  children?: React.ReactNode;
}

const OperationalDashboardShellContent: React.FC<OperationalDashboardShellContentProps> = ({ children }) => {
  const { shellData, loading, error, refetchContext } = useOperationalDashboardContext();

  return (
    <DashboardSyncProvider onRefreshNeeded={refetchContext}>
      <div className="min-h-screen p-4 md:p-5 space-y-4 bg-slate-50 text-slate-900 font-sans">
        {/* Top Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconPlantSiteDashboard className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Overall Operational Dashboard
              </h1>
              <p className="text-xs font-normal text-slate-500">
                Executive Fleet Command Tower, Operational SLAs &amp; Customer Performance Intelligence
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Dashboard Filter Bar */}
        <GlobalDashboardFilterBar />

        {/* Executive Top Ribbon Row-1 KPIs */}
        <ExecutiveKPIRibbon />

        {/* Loading Shimmer State */}
        {loading && !shellData && (
          <div className="p-6 rounded-lg bg-white border border-slate-200/90 animate-pulse flex items-center justify-center space-x-3 text-slate-500 shadow-2xs">
            <RefreshCw className="w-4 h-4 animate-spin text-blue-700" />
            <span className="text-xs font-semibold">Synchronizing Operational Context...</span>
          </div>
        )}

        {/* Error Banner State */}
        {error && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-between text-rose-800 text-xs">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => refetchContext()}
              className="px-2.5 py-1 bg-white hover:bg-rose-100 border border-rose-300 rounded-md text-rose-900 font-semibold transition"
            >
              Retry
            </button>
          </div>
        )}

        {/* Zero-Data / Empty Context Banner */}
        {!loading && shellData && shellData.metadata.total_dispatches === 0 && (
          <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center justify-between">
            <span>No canonical operational dispatches loaded for the current filter context.</span>
            <span className="font-mono text-[11px] font-semibold text-amber-900">STATUS: ABSOLUTE ZERO</span>
          </div>
        )}

        {/* Child Widgets Slot */}
        <div className="space-y-4">
          {children || (
            <div className="p-12 rounded-lg bg-white border border-slate-200/90 text-center space-y-2 shadow-2xs">
              <h3 className="text-base font-bold text-slate-800">Operational Shell Canvas Ready</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                WS-03.0 Core Shell &amp; Synchronization Engine established. Child widget modules will mount here in subsequent workstreams.
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardSyncProvider>
  );
};

export const OperationalDashboardShell: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  return (
    <DashboardFilterProvider>
      <OperationalDashboardShellContent>{children}</OperationalDashboardShellContent>
    </DashboardFilterProvider>
  );
};
