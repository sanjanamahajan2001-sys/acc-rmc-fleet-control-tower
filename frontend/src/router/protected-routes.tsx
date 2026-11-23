import { RouteObject } from 'react-router-dom';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { AppLayout } from '../layouts/AppLayout';
import { ERPImportWorkspacePage, ERPExplorerPage } from '../modules/erp';
import { ReportsManagementPage } from '../modules/reports/pages/ReportsManagementPage';
import { PlatformSettingsPage } from '../modules/settings/pages/PlatformSettingsPage';
import { UserManagementPage } from '../modules/settings/pages/UserManagementPage';


import { SiteDashboardPage } from '../modules/site_dashboard/pages/SiteDashboardPage';
import { OverallDashboardPage } from '../modules/operational_dashboard/pages/OverallDashboardPage';
import { SiteComparisonDashboardPage } from '../modules/operational_dashboard/pages/SiteComparisonDashboardPage';
import { DispatchAnalysisDashboardPage } from '../modules/operational_dashboard/pages/DispatchAnalysisDashboardPage';
import { DispatchOptimizationDashboardPage } from '../modules/operational_dashboard/pages/DispatchOptimizationDashboardPage';
import { AlertCenterDashboardPage } from '../modules/operational_dashboard/pages/AlertCenterDashboardPage';
import { TimelineReplayDashboardPage } from '../modules/operational_dashboard/pages/TimelineReplayDashboardPage';
import { OperationalIntelligencePage } from '../modules/operational_intelligence/pages/OperationalIntelligencePage';
import { PredictiveIntelligencePage } from '../modules/operational_intelligence/pages/PredictiveIntelligencePage';
import { ControlTowerActionsPage } from '../modules/operational_intelligence/pages/ControlTowerActionsPage';

import { PlatformHomePage } from '../modules/home/pages/PlatformHomePage';

export const protectedRoutes: RouteObject = {
  element: <ProtectedRoute />,
  children: [
    {
      element: <AppLayout />,
      children: [
        {
          path: '/',
          element: <PlatformHomePage />,
        },
        {
          path: '/site-dashboard',
          element: <SiteDashboardPage />,
        },
        {
          path: '/fleet/site-dashboard',
          element: <SiteDashboardPage />,
        },
        {
          path: '/overall-dashboard',
          element: <OverallDashboardPage />,
        },
        {
          path: '/fleet/overall-dashboard',
          element: <OverallDashboardPage />,
        },
        {
          path: '/site-comparison',
          element: <SiteComparisonDashboardPage />,
        },
        {
          path: '/fleet/site-comparison',
          element: <SiteComparisonDashboardPage />,
        },
        {
          path: '/dispatch-analysis',
          element: <DispatchAnalysisDashboardPage />,
        },
        {
          path: '/fleet/dispatch-analysis',
          element: <DispatchAnalysisDashboardPage />,
        },
        {
          path: '/dispatch-optimization',
          element: <DispatchOptimizationDashboardPage />,
        },
        {
          path: '/fleet/dispatch-optimization',
          element: <DispatchOptimizationDashboardPage />,
        },
        {
          path: '/alerts',
          element: <AlertCenterDashboardPage />,
        },
        {
          path: '/fleet/alerts',
          element: <AlertCenterDashboardPage />,
        },
        {
          path: '/timeline-replay',
          element: <TimelineReplayDashboardPage />,
        },
        {
          path: '/fleet/timeline-replay',
          element: <TimelineReplayDashboardPage />,
        },
        {
          path: '/operational-intelligence',
          element: <OperationalIntelligencePage />,
        },
        {
          path: '/fleet/operational-intelligence',
          element: <OperationalIntelligencePage />,
        },
        {
          path: '/predictive-intelligence',
          element: <PredictiveIntelligencePage />,
        },
        {
          path: '/fleet/predictive-intelligence',
          element: <PredictiveIntelligencePage />,
        },
        {
          path: '/control-tower-actions',
          element: <ControlTowerActionsPage />,
        },
        {
          path: '/fleet/control-tower-actions',
          element: <ControlTowerActionsPage />,
        },
        {
          path: '/erp/import',
          element: <ERPImportWorkspacePage />,
        },
        {
          path: '/erp/explorer',
          element: <ERPExplorerPage />,
        },
        {
          path: '/reports',
          element: <ReportsManagementPage />,
        },
        {
          path: '/fleet/reports',
          element: <ReportsManagementPage />,
        },
        {
          path: '/settings',
          element: <PlatformSettingsPage />,
        },
        {
          path: '/settings/users',
          element: <UserManagementPage />,
        },
      ],
    },
  ],
};
