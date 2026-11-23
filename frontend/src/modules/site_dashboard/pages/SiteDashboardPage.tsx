import { env } from '../../../config/env';
import React, { useEffect, useState } from 'react';
import { IconPlantSiteDashboard } from '../../../components/icons/LinealColorIcons';
import { KPICardGrid } from '../components/kpi/KPICardGrid';
import { KPICardData } from '../components/kpi/KPICard';
import { SiteSummaryPanel } from '../components/summary/SiteSummaryPanel';
import { TMQueueTimelineGantt, TimelineData } from '../components/timeline/TMQueueTimelineGantt';
import { QueueAnalyticsContainer, QueueAnalyticsContainerData } from '../components/queueAnalytics/QueueAnalyticsContainer';
import { QueueReasonTable } from '../components/queueAnalytics/QueueReasonTable';
import { TMDetailsContainer, TMDetailsContainerData } from '../components/tmDetails/TMDetailsContainer';
import { QueueOnArrivalWidget } from '../components/queueAnalytics/QueueOnArrivalWidget';
import { DispatchIntervalWidget } from '../components/queueAnalytics/DispatchIntervalWidget';
import { BiggestWaitingVehiclesWidget } from '../components/queueAnalytics/BiggestWaitingVehiclesWidget';
import { SitePerformanceContainer, SitePerformanceContainerData } from '../components/sitePerformance/SitePerformanceContainer';
import { FleetUtilizationContainer, FleetUtilizationContainerData } from '../components/fleetUtilization/FleetUtilizationContainer';
import { DecisionIntelligenceContainer, DecisionIntelligenceContainerData } from '../components/decisionIntelligence/DecisionIntelligenceContainer';
import { OperationalWidgetsContainer, OperationalWidgetsContainerData } from '../components/operationalWidgets/OperationalWidgetsContainer';
import { DashboardSyncProvider } from '../orchestration/DashboardSyncProvider';
import { SyncStatusHeaderBadge } from '../components/SyncStatusHeaderBadge';
import { DashboardFilterProvider, useDashboardFilters } from '../orchestration/DashboardFilterProvider';
import { GlobalDashboardFilterBar } from '../components/GlobalDashboardFilterBar';

import { SiteUnloadingLossTable, SiteUnloadingLossRowDTO } from '../components/SiteUnloadingLossTable';
import { SiteRetentionLossTable, SiteRetentionLossRowDTO } from '../components/SiteRetentionLossTable';
import { SiteHoldingLossTable, SiteHoldingLossRowDTO } from '../components/SiteHoldingLossTable';

const SiteDashboardContent: React.FC = () => {
  const { filters, updateMetadata } = useDashboardFilters();
  const [kpis, setKpis] = useState<KPICardData[]>([]);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [queueAnalyticsData, setQueueAnalyticsData] = useState<QueueAnalyticsContainerData | null>(null);
  const [tmDetailsData, setTmDetailsData] = useState<TMDetailsContainerData | null>(null);
  const [sitePerformanceData, setSitePerformanceData] = useState<SitePerformanceContainerData | null>(null);
  const [fleetUtilizationData, setFleetUtilizationData] = useState<FleetUtilizationContainerData | null>(null);
  const [decisionIntelligenceData, setDecisionIntelligenceData] = useState<DecisionIntelligenceContainerData | null>(null);
  const [operationalWidgetsData, setOperationalWidgetsData] = useState<OperationalWidgetsContainerData | null>(null);
  const [unloadingLossData, setUnloadingLossData] = useState<SiteUnloadingLossRowDTO[]>([]);
  const [unloadingLossTotalClients, setUnloadingLossTotalClients] = useState<number>(0);
  const [holdingLossData, setHoldingLossData] = useState<SiteHoldingLossRowDTO[]>([]);
  const [holdingLossTotalClients, setHoldingLossTotalClients] = useState<number>(0);
  const [retentionLossData, setRetentionLossData] = useState<SiteRetentionLossRowDTO[]>([]);
  const [retentionLossTotalClients, setRetentionLossTotalClients] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const paramsObj: Record<string, string> = {
        plant_id: filters.plant_id || 'ALL',
        customer_id: filters.customer_id || 'ALL',
        dataset_type: filters.dataset_type || 'ALL',
      };
      if (filters.operation_date) paramsObj.operation_date = filters.operation_date;
      if (filters.dataset_id) paramsObj.dataset_id = filters.dataset_id;

      const query = new URLSearchParams(paramsObj).toString();

      const tmQueryObj = { ...paramsObj, page_size: '100' };
      const tmQuery = new URLSearchParams(tmQueryObj).toString();

      const [resMaster, resQueue, resTm, resPerf, resFleet, resDecision, resWidgets, resUnloadingLoss, resHoldingLoss, resRetentionLoss] = await Promise.all([
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/queue-analytics?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/tm-details?${tmQuery}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/site-performance?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/fleet-utilization?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/decision-intelligence?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/operational-widgets?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/unloading-loss-breakdown?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/holding-loss-breakdown?${query}`),
        fetch(`${env.VITE_API_BASE_URL}/site-dashboard/retention-loss-breakdown?${query}`),
      ]);

      const dataMaster = await resMaster.json();
      const dataQueue = await resQueue.json();
      const dataTm = await resTm.json();
      const dataPerf = await resPerf.json();
      const dataFleet = await resFleet.json();
      const dataDecision = await resDecision.json();
      const dataWidgets = await resWidgets.json();
      const dataUnloadingLoss = await resUnloadingLoss.json();
      const dataHoldingLoss = await resHoldingLoss.json();
      const dataRetentionLoss = await resRetentionLoss.json();

      if (dataMaster.success && dataMaster.data) {
        const master = dataMaster.data;
        setKpis([
          master.kpis.dispatches,
          master.kpis.holding,
          master.kpis.retention,
          master.kpis.overlap,
          master.kpis.accuracy,
        ]);
        setSummaryData(master.summary);
        setTimelineData(master.timeline);
      }

      if (dataQueue.success && dataQueue.data) {
        setQueueAnalyticsData(dataQueue.data);
      }

      if (dataTm.success && dataTm.data) {
        setTmDetailsData(dataTm.data);
      }

      if (dataPerf.success && dataPerf.data) {
        setSitePerformanceData(dataPerf.data);
      }

      if (dataFleet.success && dataFleet.data) {
        setFleetUtilizationData(dataFleet.data);
      }

      if (dataDecision.success && dataDecision.data) {
        setDecisionIntelligenceData(dataDecision.data);
      }

      if (dataWidgets.success && dataWidgets.data) {
        setOperationalWidgetsData(dataWidgets.data);
      }

      if (dataUnloadingLoss.success && dataUnloadingLoss.data) {
        setUnloadingLossData(dataUnloadingLoss.data.data || []);
        setUnloadingLossTotalClients(dataUnloadingLoss.data.total_affected_clients || 0);
      }

      if (dataHoldingLoss.success && dataHoldingLoss.data) {
        setHoldingLossData(dataHoldingLoss.data.data || []);
        setHoldingLossTotalClients(dataHoldingLoss.data.total_affected_clients || 0);
      }

      if (dataRetentionLoss.success && dataRetentionLoss.data) {
        setRetentionLossData(dataRetentionLoss.data.data || []);
        setRetentionLossTotalClients(dataRetentionLoss.data.total_affected_clients || 0);
      }
    } catch (e) {
      // Fallback display
      setKpis([
        { key: 'dispatches', label: 'Total Dispatches', current_value: 0, unit: 'Trips', status: 'OPTIMAL' },
        { key: 'holding', label: 'Holding Beyond 20 min', current_value: 0.0, unit: 'hrs', threshold: 5.0, status: 'OPTIMAL' },
        { key: 'retention', label: 'Retention Beyond 10 min', current_value: 0.0, unit: 'hrs', threshold: 3.0, status: 'OPTIMAL' },
        { key: 'overlap', label: 'TM Overlap (Weighted)', current_value: 0.0, unit: 'TM-min', threshold: 60.0, status: 'OPTIMAL' },
        { key: 'accuracy', label: 'Dispatch Accuracy', current_value: 100.0, unit: '%', target: 90.0, variance: 10.0, status: 'OPTIMAL' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardSyncProvider onRefreshNeeded={fetchDashboardData}>
      <div className="min-h-screen p-4 md:p-5 space-y-4 bg-slate-50 text-slate-900 font-sans">
        {/* Top Bar Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconPlantSiteDashboard className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Site Operational Intelligence Dashboard
              </h1>
              <p className="text-xs font-normal text-slate-500">
                Real-time Concrete Batching, Dispatch SLAs & TM Queue Monitoring
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Workstream 2.2 Global Dashboard Filter Bar */}
        <GlobalDashboardFilterBar />

        {/* Workstream 2.2 KPI Intelligence Cards */}
        <KPICardGrid cards={kpis} summaryData={summaryData} customerId={filters.customer_id} loading={loading} />

        {/* Master Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 pt-1">
          {/* Left Column (3/4 Width): Core Operational Intelligence Panels */}
          <div className="lg:col-span-3 space-y-4">
            {/* Workstream 2.4 TM Queue Timeline (Gantt Engine) */}
            <TMQueueTimelineGantt data={timelineData} loading={loading} />

            {/* Side-by-Side Row: Queue Analytics (Left) & TM Details (Right) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Workstream 2.5 Queue Analytics & Operational Trend Intelligence */}
              <QueueAnalyticsContainer data={queueAnalyticsData} timelineData={timelineData} loading={loading} />

              {/* Workstream 2.6 TM Details & Dispatch Intelligence Subsystem */}
              <TMDetailsContainer data={tmDetailsData} loading={loading} />
            </div>
          </div>

          {/* Right Column (1/4 Width): Top 5 Sites, Site Summary, and WHY DID QUEUE BUILD UP? */}
          <div className="lg:col-span-1 space-y-4">
            <SiteSummaryPanel data={summaryData} customerId={filters.customer_id} loading={loading} />
            
            {/* WHY DID QUEUE BUILD UP? Widget in Right Column */}
            <QueueReasonTable causes={queueAnalyticsData?.root_causes || []} />
          </div>
        </div>

        {/* NEW UNIFIED 3-COLUMN GRID: Unloading (>60m), Holding (>20m), and Retention (>10m) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <SiteUnloadingLossTable
            data={unloadingLossData}
            totalAffectedClients={unloadingLossTotalClients}
            loading={loading}
          />
          <SiteHoldingLossTable
            data={holdingLossData}
            totalAffectedClients={holdingLossTotalClients}
            loading={loading}
          />
          <SiteRetentionLossTable
            data={retentionLossData}
            totalAffectedClients={retentionLossTotalClients}
            loading={loading}
          />
        </div>

        {/* Full-Width 3-Column Bottom Row: Spans 100% width across screen eliminating right blank space */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QueueOnArrivalWidget timelineData={timelineData} loading={loading} />
          <DispatchIntervalWidget timelineData={timelineData} loading={loading} />
          <BiggestWaitingVehiclesWidget tmDetailsData={tmDetailsData} loading={loading} />
        </div>
      </div>
    </DashboardSyncProvider>
  );
};

export const SiteDashboardPage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <SiteDashboardContent />
    </DashboardFilterProvider>
  );
};

export default SiteDashboardPage;
