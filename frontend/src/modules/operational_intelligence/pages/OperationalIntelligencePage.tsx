import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';
import { IconOperationalPulse, IconPredictiveRadar } from '../../../components/icons/LinealColorIcons';
import { Link } from 'react-router-dom';
import { env } from '../../../config/env';
import {
  DashboardFilterProvider,
  useDashboardFilters,
} from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { SECTION_REGISTRY_CONFIGS } from '../registry/sectionRegistry';
import { SectionRenderer } from '../components/SectionRenderer';

import {
  OperationalHealthSection,
  OperationalHealthData,
} from '../components/OperationalHealthSection';
import {
  OperationalAlertIntelligenceSection,
  OperationalAlertIntelligenceData,
} from '../components/OperationalAlertIntelligenceSection';
import {
  OperationalDecisionRecommendationsSection,
  OperationalDecisionRecommendationData,
} from '../components/OperationalDecisionRecommendationsSection';
import {
  OperationalFinancialExposureSection,
  OperationalFinancialExposureData,
} from '../components/OperationalFinancialExposureSection';
import {
  OperationalFleetEfficiencySection,
  OperationalFleetEfficiencyData,
} from '../components/OperationalFleetEfficiencySection';
import {
  OperationalCostExposureSection,
  OperationalCostExposureData,
} from '../components/OperationalCostExposureSection';

const OperationalIntelligencePageContent: React.FC = () => {
  const { filters } = useDashboardFilters();

  // Section 01: Operational Health
  const [healthData, setHealthData] = useState<OperationalHealthData | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Section 02: Alert Intelligence
  const [alertsData, setAlertsData] = useState<OperationalAlertIntelligenceData | null>(null);
  const [alertsLoading, setAlertsLoading] = useState<boolean>(true);
  const [alertsError, setAlertsError] = useState<string | null>(null);

  // Section 03: Decision Recommendations
  const [recsData, setRecsData] = useState<OperationalDecisionRecommendationData | null>(null);
  const [recsLoading, setRecsLoading] = useState<boolean>(true);
  const [recsError, setRecsError] = useState<string | null>(null);

  // Section 04: Financial Exposure
  const [finData, setFinData] = useState<OperationalFinancialExposureData | null>(null);
  const [finLoading, setFinLoading] = useState<boolean>(true);
  const [finError, setFinError] = useState<string | null>(null);

  // Section 05: Fleet Efficiency
  const [effData, setEffData] = useState<OperationalFleetEfficiencyData | null>(null);
  const [effLoading, setEffLoading] = useState<boolean>(true);
  const [effError, setEffError] = useState<string | null>(null);

  // Section 06: Cost & Exposure
  const [costData, setCostData] = useState<OperationalCostExposureData | null>(null);
  const [costLoading, setCostLoading] = useState<boolean>(true);
  const [costError, setCostError] = useState<string | null>(null);
  const [costPage, setCostPage] = useState<number>(1);
  const latestCostRequestIdRef = useRef<number>(0);

  // Fetch callbacks
  const fetchHealthData = useCallback(async () => {
    try {
      setHealthLoading(true);
      setHealthError(null);

      const qs = new URLSearchParams({
        ...(filters.plant_id && filters.plant_id !== 'ALL' ? { plant_id: filters.plant_id } : {}),
        ...(filters.customer_id && filters.customer_id !== 'ALL' ? { customer_id: filters.customer_id } : {}),
        ...(filters.dataset_type ? { dataset_type: filters.dataset_type } : {}),
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/health?${qs}`);
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to calculate operational health');
      }

      setHealthData(body.data);
    } catch (err: any) {
      setHealthError(err.message || 'Error fetching operational health');
    } finally {
      setHealthLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const fetchAlertsData = useCallback(async () => {
    try {
      setAlertsLoading(true);
      setAlertsError(null);

      const qs = new URLSearchParams({
        ...(filters.plant_id && filters.plant_id !== 'ALL' ? { plant_id: filters.plant_id } : {}),
        ...(filters.customer_id && filters.customer_id !== 'ALL' ? { customer_id: filters.customer_id } : {}),
        ...(filters.dataset_type ? { dataset_type: filters.dataset_type } : {}),
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/alerts?${qs}`);
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to calculate alert intelligence');
      }

      setAlertsData(body.data);
    } catch (err: any) {
      setAlertsError(err.message || 'Error fetching alert intelligence');
    } finally {
      setAlertsLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const fetchRecsData = useCallback(async () => {
    try {
      setRecsLoading(true);
      setRecsError(null);

      const qs = new URLSearchParams({
        ...(filters.plant_id && filters.plant_id !== 'ALL' ? { plant_id: filters.plant_id } : {}),
        ...(filters.customer_id && filters.customer_id !== 'ALL' ? { customer_id: filters.customer_id } : {}),
        ...(filters.dataset_type ? { dataset_type: filters.dataset_type } : {}),
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/recommendations?${qs}`);
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to calculate recommendations');
      }

      setRecsData(body.data);
    } catch (err: any) {
      setRecsError(err.message || 'Error fetching recommendations');
    } finally {
      setRecsLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const fetchFinData = useCallback(async () => {
    try {
      setFinLoading(true);
      setFinError(null);

      const qs = new URLSearchParams({
        ...(filters.plant_id && filters.plant_id !== 'ALL' ? { plant_id: filters.plant_id } : {}),
        ...(filters.customer_id && filters.customer_id !== 'ALL' ? { customer_id: filters.customer_id } : {}),
        ...(filters.dataset_type ? { dataset_type: filters.dataset_type } : {}),
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/financial?${qs}`);
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to calculate financial exposure');
      }

      setFinData(body.data);
    } catch (err: any) {
      setFinError(err.message || 'Error fetching financial exposure');
    } finally {
      setFinLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const fetchEffData = useCallback(async () => {
    try {
      setEffLoading(true);
      setEffError(null);

      const qs = new URLSearchParams({
        ...(filters.plant_id && filters.plant_id !== 'ALL' ? { plant_id: filters.plant_id } : {}),
        ...(filters.customer_id && filters.customer_id !== 'ALL' ? { customer_id: filters.customer_id } : {}),
        ...(filters.dataset_type ? { dataset_type: filters.dataset_type } : {}),
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/efficiency?${qs}`);
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to calculate fleet efficiency');
      }

      setEffData(body.data);
    } catch (err: any) {
      setEffError(err.message || 'Error fetching fleet efficiency');
    } finally {
      setEffLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const fetchCostData = useCallback(async (targetPage: number = 1) => {
    const currentRequestId = ++latestCostRequestIdRef.current;

    try {
      setCostLoading(true);
      setCostError(null);

      const qs = new URLSearchParams({
        ...(filters.plant_id && filters.plant_id !== 'ALL' ? { plant_id: filters.plant_id } : {}),
        ...(filters.customer_id && filters.customer_id !== 'ALL' ? { customer_id: filters.customer_id } : {}),
        ...(filters.dataset_type ? { dataset_type: filters.dataset_type } : {}),
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
        page: String(targetPage),
        page_size: '10',
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/cost-exposure?${qs}`);
      const body = await res.json();

      if (currentRequestId !== latestCostRequestIdRef.current) {
        return;
      }

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to calculate cost & exposure intelligence');
      }

      setCostData(body.data);
    } catch (err: any) {
      if (currentRequestId === latestCostRequestIdRef.current) {
        setCostError(err.message || 'Error fetching cost & exposure intelligence');
      }
    } finally {
      if (currentRequestId === latestCostRequestIdRef.current) {
        setCostLoading(false);
      }
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id]);

  const handleCostPageChange = useCallback((newPage: number) => {
    setCostPage(newPage);
    fetchCostData(newPage);
  }, [fetchCostData]);

  const masterRefresh = useCallback(() => {
    fetchHealthData();
    fetchAlertsData();
    fetchRecsData();
    fetchFinData();
    fetchEffData();
    setCostPage(1);
    fetchCostData(1);
  }, [fetchHealthData, fetchAlertsData, fetchRecsData, fetchFinData, fetchEffData, fetchCostData]);

  useEffect(() => {
    masterRefresh();
  }, [masterRefresh]);

  const healthConfig = SECTION_REGISTRY_CONFIGS.SECTION_01_OPERATIONAL_HEALTH;
  const alertConfig = SECTION_REGISTRY_CONFIGS.SECTION_02_ALERTS_INTELLIGENCE;
  const recsConfig = SECTION_REGISTRY_CONFIGS.SECTION_03_DECISION_RECOMMENDATIONS;
  const finConfig = SECTION_REGISTRY_CONFIGS.SECTION_04_FINANCIAL_EXPOSURE;
  const effConfig = SECTION_REGISTRY_CONFIGS.SECTION_05_FLEET_EFFICIENCY;
  const costConfig = SECTION_REGISTRY_CONFIGS.SECTION_06_COST_EXPOSURE;

  return (
    <DashboardSyncProvider onRefreshNeeded={masterRefresh}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Sub-Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconOperationalPulse className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Operational Intelligence Control Room
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Operational health, active exception triage, predictive recommendations, and financial exposure analytics
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Filter Control Bar */}
        <GlobalDashboardFilterBar />

        {/* Predictive Intelligence CTA Navigation Banner */}
        <div className="border border-slate-200/90 rounded-lg p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs bg-white">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconPredictiveRadar className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900">Predictive Intelligence Active</h3>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border bg-emerald-50 border-emerald-200 text-emerald-700">
                  ONLINE
                </span>
              </div>
              <p className="text-xs font-medium mt-0.5 text-slate-500">
                ML risk forecasting, INR financial exposure projections, and proactive dispatch suggestions are active.
              </p>
            </div>
          </div>
          <Link
            to="/predictive-intelligence"
            className="px-3.5 py-2 rounded-md text-xs font-bold text-white bg-blue-700 hover:bg-blue-800 flex items-center gap-2 transition shadow-xs shrink-0"
          >
            <span>Open Predictive Intelligence</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Section 01: Operational Health & Executive Index */}
        <SectionRenderer
          config={healthConfig}
          loading={healthLoading}
          error={healthError}
          calculationStatus={healthData?.calculation_status}
          calculationNotes={healthData?.calculation_notes}
          onRetry={fetchHealthData}
        >
          <OperationalHealthSection data={healthData} />
        </SectionRenderer>

        {/* Section 02: Operational Alert Intelligence */}
        <SectionRenderer
          config={alertConfig}
          loading={alertsLoading}
          error={alertsError}
          calculationStatus={alertsData?.calculation_status}
          calculationNotes={alertsData?.calculation_notes}
          onRetry={fetchAlertsData}
        >
          <OperationalAlertIntelligenceSection data={alertsData} />
        </SectionRenderer>

        {/* Section 03: Actionable Decision Recommendations */}
        <SectionRenderer
          config={recsConfig}
          loading={recsLoading}
          error={recsError}
          calculationStatus={recsData?.calculation_status}
          calculationNotes={recsData?.calculation_notes}
          onRetry={fetchRecsData}
        >
          <OperationalDecisionRecommendationsSection data={recsData} />
        </SectionRenderer>

        {/* Section 04: Financial Loss & SLA Risk Exposure */}
        <SectionRenderer
          config={finConfig}
          loading={finLoading}
          error={finError}
          calculationStatus={finData?.calculation_status}
          calculationNotes={finData?.calculation_notes}
          onRetry={fetchFinData}
        >
          <OperationalFinancialExposureSection data={finData} />
        </SectionRenderer>

        {/* Section 05: Fleet & Plant Operational Efficiency */}
        <SectionRenderer
          config={effConfig}
          loading={effLoading}
          error={effError}
          calculationStatus={effData?.calculation_status}
          calculationNotes={effData?.calculation_notes}
          onRetry={fetchEffData}
        >
          <OperationalFleetEfficiencySection data={effData} />
        </SectionRenderer>

        {/* Section 06: Cost & Exposure Intelligence */}
        <SectionRenderer
          config={costConfig}
          loading={costLoading}
          error={costError}
          calculationStatus={costData?.calculation_status as 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR' | undefined}
          calculationNotes={costData?.calculation_notes}
          onRetry={() => {
            setCostPage(1);
            fetchCostData(1);
          }}
        >
          <OperationalCostExposureSection
            data={costData}
            onPageChange={handleCostPageChange}
          />
        </SectionRenderer>
      </div>
    </DashboardSyncProvider>
  );
};

export const OperationalIntelligencePage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <OperationalIntelligencePageContent />
    </DashboardFilterProvider>
  );
};

export default OperationalIntelligencePage;
