import React, { useState } from 'react';
import { IconCycleStopwatch, IconRouteDirection, IconAnalyticsBarChart } from '../../../components/icons/LinealColorIcons';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { DashboardFilterProvider } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { useOperationalDashboardContext } from '../hooks/useOperationalDashboardContext';

import { DispatchAnalysisKPIRow1 } from '../components/DispatchAnalysisKPIRow1';
import { DispatchAnalysisKPIRow2 } from '../components/DispatchAnalysisKPIRow2';
import { DispatchCadenceTable } from '../components/DispatchCadenceTable';
import { DispatchDelayAnalyticsWidget } from '../components/DispatchDelayAnalyticsWidget';
import { OperationalInsightsWidget } from '../components/OperationalInsightsWidget';
import { CustomerVehicleReportWidget } from '../components/CustomerVehicleReportWidget';
import { RouteAnalysisWorkspace } from '../components/RouteAnalysis/RouteAnalysisWorkspace';

type ActiveTab = 'cadence' | 'route_analysis';

const DispatchAnalysisDashboardContent: React.FC = () => {
  const { refetchContext } = useOperationalDashboardContext();
  const [activeTab, setActiveTab] = useState<ActiveTab>('cadence');

  return (
    <DashboardSyncProvider onRefreshNeeded={refetchContext}>
      <div className="min-h-screen p-4 md:p-5 space-y-5 bg-slate-50 text-slate-900">
        {/* Top Header Bar with Workspace Switcher Tabs */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg shadow-2xs border border-slate-200/90 bg-white">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              {activeTab === 'cadence' ? <IconCycleStopwatch className="w-6 h-6" /> : <IconRouteDirection className="w-6 h-6" />}
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-slate-900">
                Dispatch Analysis &amp; Route Optimization
              </h1>
              <p className="text-xs font-medium text-slate-500">
                {activeTab === 'cadence'
                  ? 'Fleet dispatch pacing, interval variance, queue delay analytics & customer-vehicle matrix'
                  : 'Deterministic 2D Evidence Decision Support Engine (ERP T1 Operational Transit + Google Traffic ETA)'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Workspace View Switcher Tabs */}
            <div className="flex items-center p-1 rounded-lg border border-slate-200 bg-slate-100 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setActiveTab('cadence')}
                data-testid="tab-dispatch-cadence"
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                  activeTab === 'cadence'
                    ? 'bg-white text-blue-700 shadow-2xs font-bold border border-slate-200/90'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <IconAnalyticsBarChart className="w-3.5 h-3.5" />
                <span>Cadence &amp; Delay Analytics</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('route_analysis')}
                data-testid="tab-route-analysis"
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
                  activeTab === 'route_analysis'
                    ? 'bg-white text-blue-700 shadow-2xs font-bold border border-slate-200/90'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <IconRouteDirection className="w-3.5 h-3.5" />
                <span>Route Analysis (Decision Support)</span>
              </button>
            </div>

            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Dashboard Filter Bar (Shared filter provider contract) */}
        <GlobalDashboardFilterBar />

        {/* Tab 1: Cadence & Delay Analytics Workspace */}
        {activeTab === 'cadence' && (
          <div className="space-y-6" data-testid="cadence-analytics-workspace">
            {/* Row 1 KPIs (5 KPIs) */}
            <DispatchAnalysisKPIRow1 />

            {/* Row 2 KPIs (5 KPIs) */}
            <DispatchAnalysisKPIRow2 />

            {/* Dispatch Cadence & Variance Table */}
            <DispatchCadenceTable />

            {/* Dispatch Delay Analytics Widget & Operational Insights Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DispatchDelayAnalyticsWidget />
              <OperationalInsightsWidget />
            </div>

            {/* Customer Report & Vehicle Performance Matrix */}
            <CustomerVehicleReportWidget />
          </div>
        )}

        {/* Tab 2: Route Analysis Decision Support Workspace */}
        {activeTab === 'route_analysis' && (
          <div className="space-y-6" data-testid="route-analysis-decision-workspace">
            <RouteAnalysisWorkspace />
          </div>
        )}
      </div>
    </DashboardSyncProvider>
  );
};

export const DispatchAnalysisDashboardPage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <DispatchAnalysisDashboardContent />
    </DashboardFilterProvider>
  );
};

export default DispatchAnalysisDashboardPage;
