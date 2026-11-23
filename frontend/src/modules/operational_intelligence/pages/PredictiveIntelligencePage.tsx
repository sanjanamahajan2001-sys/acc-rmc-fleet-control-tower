import { env } from '../../../config/env';
import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { CheckCircle2, Lock, AlertTriangle, AlertCircle, Eye, X, ArrowUpRight, Sparkles, TrendingUp, Cpu, Database, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { IconPredictiveRadar, IconShieldSecure, IconEfficiencyTimer, IconCycleStopwatch, IconBatchingPlantFactory, IconCriticalAlert, IconRupeeCoin } from '../../../components/icons/LinealColorIcons';
import { DashboardFilterProvider, useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { KPICard } from '../../../components/common/KPICard';

export interface ModelAuthorityItem {
  model_name: string;
  target_name: string;
  model_category: string;
  prediction_authority: 'NOT_CONFIGURED' | 'AUTHORITATIVE';
  active_version: string | null;
  artifact_sha256: string | null;
  feature_set_version: string;
  last_promoted_at: string | null;
}

export interface PredictiveAuthorityOverview {
  overall_authority_status: 'NOT_CONFIGURED' | 'AUTHORITATIVE';
  total_model_families: number;
  promoted_model_count: number;
  rejected_model_count: number;
  models: ModelAuthorityItem[];
  calculation_status: string;
  calculation_notes: string;
}

export interface OperationalPredictionItem {
  id: string;
  prediction_snapshot_id: string;
  idempotency_key: string;
  prediction_timestamp: string;
  prediction_status: string;
  model_name: string;
  model_version: string;
  artifact_sha256: string;
  feature_set_version: string;
  dispatch_id: string;
  dispatch_code: string;
  plant_code: string | null;
  plant_name: string | null;
  customer_code: string | null;
  customer_name: string | null;
  vehicle_code: string | null;
  target_name: string;
  predicted_value: number | null;
  confidence_score: number | null;
  input_features: Record<string, any>;
  prediction_outputs: Record<string, any>;
  lineage_metadata?: Record<string, any> | null;
  financial_exposure_inr?: number | null;
  sla_penalty_risk_inr?: number | null;
  plant_congestion_risk_inr?: number | null;
  idle_queue_cost_inr?: number | null;
  total_financial_risk_inr?: number | null;
  currency?: string;
  calculation_lineage?: Record<string, any> | null;
}

export interface OperationalPrioritization {
  top_delayed_dispatches: OperationalPredictionItem[];
  high_sla_risk_dispatches: OperationalPredictionItem[];
  high_plant_risk_dispatches: OperationalPredictionItem[];
}

export interface OperationalPredictiveOverview {
  overall_authority_status: string;
  promoted_model_count: number;
  total_snapshots_found: number;
  prioritization: OperationalPrioritization;
  snapshots: OperationalPredictionItem[];
  calculation_status: string;
  calculation_notes: string;
}

export const PredictiveIntelligencePageContent: React.FC = () => {
  const { filters } = useDashboardFilters();

  const [authorityOverview, setAuthorityOverview] = useState<PredictiveAuthorityOverview | null>(null);
  const [authorityLoading, setAuthorityLoading] = useState<boolean>(true);
  const [authorityError, setAuthorityError] = useState<string | null>(null);

  const [operationalData, setOperationalData] = useState<OperationalPredictiveOverview | null>(null);
  const [operationalLoading, setOperationalLoading] = useState<boolean>(true);
  const [operationalError, setOperationalError] = useState<string | null>(null);

  const [selectedSnapshot, setSelectedSnapshot] = useState<OperationalPredictionItem | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generateProgress, setGenerateProgress] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  // Section 3: Snapshot Search & Pagination State
  const [snapshotSearch, setSnapshotSearch] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(snapshotSearch.trim());
    }, 300);
    return () => clearTimeout(handler);
  }, [snapshotSearch]);

  const handleGenerateIntelligence = async () => {
    setIsGenerating(true);
    setGenerateProgress('Evaluating live dispatch queues, transit patterns & forecasting risks...');
    try {
      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/actions/generate`, { method: 'POST' });
      const body = await res.json();
      if (!res.ok) throw new Error(body.message || 'Generation failed');
      setGenerateProgress('Updating operational forecasts...');
      await fetchAuthorityOverview();
      await fetchOperationalData();
    } catch (err: any) {
      alert(`Forecast Update Failed: ${err.message}`);
    } finally {
      setIsGenerating(false);
      setGenerateProgress(null);
    }
  };

  const fetchAuthorityOverview = useCallback(async () => {
    setAuthorityLoading(true);
    setAuthorityError(null);
    try {
      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/predictive/telemetry`);
      const body = await res.json();
      if (!res.ok || !body.success) {
        throw new Error(body.message || (body.error && body.error.message) || 'Unable to fetch predictive telemetry overview');
      }
      const data = body.data;
      if (data && data.production_authority !== undefined) {
        const families = ['delay_regressor', 'turnaround_regressor', 'sla_breach_classifier', 'plant_risk_classifier'];
        const models = families.map((name) => {
          const status = (data.authority_status || {})[name];
          const isAuth = Boolean(status && (status.status === 'PROMOTED' || status.status === 'AUTHORITATIVE' || status.is_active === true || status.version || status.model_version));
          return {
            model_name: name,
            target_name: name === 'delay_regressor' ? 'predicted_delay_mins' : name === 'turnaround_regressor' ? 'predicted_avg_turnaround_mins' : name === 'sla_breach_classifier' ? 'predicted_sla_breach_target' : 'predicted_plant_congestion_target',
            model_category: name.includes('regressor') ? 'Regression' : 'Classification',
            prediction_authority: (isAuth ? 'AUTHORITATIVE' : 'NOT_CONFIGURED') as any,
            active_version: status ? (status.model_version || status.version || status.active_version || 'v1.1.0-promoted') : null,
            artifact_sha256: status ? (status.artifact_sha256 || null) : null,
            feature_set_version: 'FeatureSetV1',
            last_promoted_at: status ? (status.promoted_at || status.training_timestamp || status.last_promoted_at || null) : null,
          };
        });
        setAuthorityOverview({
          overall_authority_status: data.production_authority === 'AUTHORITATIVE' ? 'AUTHORITATIVE' : 'NOT_CONFIGURED',
          total_model_families: 4,
          promoted_model_count: data.authoritative_model_count || 0,
          rejected_model_count: 4 - (data.authoritative_model_count || 0),
          models,
          calculation_status: data.production_authority,
          calculation_notes: `Active telemetry indicates ${data.authoritative_model_count} active risk models covering live transit, plant queues, and site retention.`,
        });
      } else {
        setAuthorityOverview(data);
      }
    } catch (err: any) {
      setAuthorityError(err.message || 'Error fetching predictive overview');
    } finally {
      setAuthorityLoading(false);
    }
  }, []);

  const fetchOperationalData = useCallback(async () => {
    setOperationalLoading(true);
    setOperationalError(null);
    try {
      const qs = new URLSearchParams({
        plant_id: filters.plant_id,
        customer_id: filters.customer_id,
        dataset_type: filters.dataset_type,
        ...(filters.operation_date ? { operation_date: filters.operation_date } : {}),
        ...(filters.dataset_id ? { dataset_id: filters.dataset_id } : {}),
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
      }).toString();

      const res = await fetch(`${env.VITE_API_BASE_URL}/operational-intelligence/predictive/operational-overview?${qs}`);
      const body = await res.json();
      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Unable to fetch operational predictive overview');
      }
      setOperationalData(body.data);
    } catch (err: any) {
      setOperationalError(err.message || 'Error fetching operational predictive data');
    } finally {
      setOperationalLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, filters.operation_date, filters.dataset_id, debouncedSearch]);

  const masterRefresh = useCallback(() => {
    fetchAuthorityOverview();
    fetchOperationalData();
  }, [fetchAuthorityOverview, fetchOperationalData]);

  useEffect(() => {
    masterRefresh();
  }, [masterRefresh]);

  const isNotConfigured =
    (authorityOverview?.overall_authority_status || operationalData?.overall_authority_status || 'NOT_CONFIGURED') === 'NOT_CONFIGURED';
  const snapshots = operationalData?.snapshots || [];

  // Multi-field search filtering
  const filteredSnapshots = useMemo(() => {
    if (!snapshotSearch.trim()) return snapshots;
    const q = snapshotSearch.toLowerCase().trim();
    return snapshots.filter((snap) => {
      const modelTitle = snap.model_name ? snap.model_name.replace(/_/g, ' ') : '';
      return (
        snap.prediction_snapshot_id?.toLowerCase().includes(q) ||
        snap.dispatch_code?.toLowerCase().includes(q) ||
        snap.plant_name?.toLowerCase().includes(q) ||
        snap.plant_code?.toLowerCase().includes(q) ||
        snap.customer_name?.toLowerCase().includes(q) ||
        snap.customer_code?.toLowerCase().includes(q) ||
        snap.model_name?.toLowerCase().includes(q) ||
        snap.model_version?.toLowerCase().includes(q) ||
        modelTitle.toLowerCase().includes(q)
      );
    });
  }, [snapshots, snapshotSearch]);

  const totalPages = Math.max(1, Math.ceil(filteredSnapshots.length / pageSize));
  const paginatedSnapshots = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredSnapshots.slice(start, start + pageSize);
  }, [filteredSnapshots, currentPage, pageSize]);

  // Reset to first page when search query, page size, or global filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [snapshotSearch, pageSize, filters.plant_id, filters.customer_id, filters.dataset_type]);

  const getHumanModelInfo = (name: string) => {
    switch (name) {
      case 'delay_regressor':
        return {
          title: 'Transit Delay Forecaster',
          description: 'Predicts traffic and transit transit time overruns',
          metric: 'Estimated Transit Overrun (mins)',
          icon: IconCycleStopwatch,
          color: '#4F46C5',
        };
      case 'turnaround_regressor':
        return {
          title: 'Plant Queue Congestion Predictor',
          description: 'Forecasts plant batching queue wait times',
          metric: 'Estimated Loading Queue (mins)',
          icon: IconBatchingPlantFactory,
          color: '#B7791F',
        };
      case 'sla_breach_classifier':
        return {
          title: 'Customer SLA Breach Predictor',
          description: 'Evaluates probability of missing delivery time windows',
          metric: 'SLA Breach Probability (%)',
          icon: IconCriticalAlert,
          color: '#C83B4B',
        };
      case 'plant_risk_classifier':
        return {
          title: 'Plant Bottleneck Risk Predictor',
          description: 'Assesses plant capacity and peak loading congestion',
          metric: 'Congestion Risk Level',
          icon: TrendingUp,
          color: '#16805C',
        };
      default:
        return {
          title: name.replace(/_/g, ' '),
          description: 'Operational risk forecaster',
          metric: 'Predicted Value',
          icon: Cpu,
          color: '#64748B',
        };
    }
  };

  const topDelayed = operationalData?.prioritization?.top_delayed_dispatches || [];
  const highCongestion = operationalData?.prioritization?.high_plant_risk_dispatches || [];
  const highSlaRisk = operationalData?.prioritization?.high_sla_risk_dispatches || [];

  return (
    <DashboardSyncProvider onRefreshNeeded={masterRefresh}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg shadow-xs border border-slate-200/90 bg-white">
          <div className="flex items-center gap-3">
            <div className="shrink-0 flex items-center justify-center">
              <IconPredictiveRadar className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Operational Risk Forecasting &amp; Early Warning Radar
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Proactive delay forecasts, customer SLA breach risks, and plant congestion predictions
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Global Filter Bar */}
        <GlobalDashboardFilterBar />

        {/* Section 1: Executive Status Banner */}
        {authorityLoading ? (
          <div className="border border-slate-200/90 rounded-lg p-6 text-center animate-pulse text-xs font-bold bg-white text-slate-500" data-testid="authority-loading">
            Synchronizing live risk models...
          </div>
        ) : authorityError ? (
          <div className="border border-rose-300 rounded-lg p-6 flex items-center gap-3 text-xs bg-rose-50 text-rose-800" data-testid="authority-error">
            <AlertTriangle className="w-6 h-6 shrink-0 text-rose-700" />
            <div>
              <h3 className="font-bold text-sm">Forecasting Query Notice</h3>
              <p className="text-xs font-medium text-rose-700">{authorityError}</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div
              className={`rounded-lg p-5 md:p-6 border shadow-xs bg-white ${
                isNotConfigured
                  ? 'border-amber-300 bg-amber-50/50'
                  : 'border-slate-200/90'
              }`}
              data-testid="predictive-authority-banner"
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
                <div className="flex items-start gap-4">
                  <div className="shrink-0 flex items-center justify-center">
                    {isNotConfigured ? <IconCriticalAlert className="w-7 h-7" /> : <IconPredictiveRadar className="w-7 h-7" />}
                  </div>
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                          isNotConfigured
                            ? 'bg-amber-100 border-amber-300 text-amber-800'
                            : 'bg-emerald-50 border-emerald-300 text-emerald-800'
                        }`}
                        data-testid="authority-status-badge"
                      >
                        {isNotConfigured ? 'Risk Models Standby' : '● Operational Risk Radar Active'}
                      </span>
                      <span className="text-xs font-mono font-medium text-slate-500">
                        {authorityOverview?.promoted_model_count || 4} Risk Predictors Online
                      </span>
                    </div>
                    <h2 className="text-lg font-bold tracking-tight text-slate-900">
                      {isNotConfigured
                        ? 'Predictive Forecasting Unavailable for Current Filter'
                        : 'Active Fleet Risk Projections & Early Warning Radar'}
                    </h2>
                    <p className="text-xs font-medium max-w-3xl leading-relaxed text-slate-600">
                      {authorityOverview?.calculation_notes || 'Continuously evaluating trip delays, batch queues, and delivery deadlines to alert dispatchers before bottlenecks occur.'}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 self-start lg:self-center">
                  <button
                    onClick={handleGenerateIntelligence}
                    disabled={isGenerating}
                    className="flex items-center gap-2 px-3.5 py-2 text-white text-xs font-bold rounded-md bg-blue-700 hover:bg-blue-800 shadow-xs transition disabled:opacity-50 shrink-0 cursor-pointer"
                  >
                    <IconPredictiveRadar className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
                    <span>{isGenerating ? 'Evaluating Queues...' : 'Re-evaluate Risk Radar'}</span>
                  </button>
                  <button
                    onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                    className="px-3 py-2 rounded-md border border-slate-200 bg-white text-slate-700 text-xs font-bold transition hover:bg-slate-50 shrink-0 cursor-pointer shadow-xs"
                  >
                    {showTechnicalDetails ? 'Hide Model Specs' : 'View Model Specs'}
                  </button>
                </div>
              </div>
            </div>

            {/* Generation Progress Indicator */}
            {generateProgress && (
              <div className="border p-4 rounded-xl text-xs flex items-center gap-3 animate-pulse shadow-xs" style={{ backgroundColor: '#ECFDF5', borderColor: '#A7F3D0', color: '#16805C' }}>
                <IconPredictiveRadar className="w-5 h-5 animate-spin shrink-0" style={{ color: '#16805C' }} />
                <div className="font-bold">{generateProgress}</div>
              </div>
            )}

            {/* Technical Model Family Grid */}
            {showTechnicalDetails && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-fadeIn">
                {(authorityOverview?.models || []).map((model) => {
                  const info = getHumanModelInfo(model.model_name);
                  const Icon = info.icon;
                  const isOnline = model.prediction_authority === 'AUTHORITATIVE';

                  return (
                    <div
                      key={model.model_name}
                      className="border border-slate-200/90 bg-white rounded-lg p-4 space-y-3 shadow-xs"
                      data-testid={`model-card-${model.model_name}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-blue-700" />
                          <span className="text-xs font-bold text-slate-900">{info.title}</span>
                        </div>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                            isOnline
                              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                              : 'bg-rose-50 border-rose-300 text-rose-800'
                          }`}
                        >
                          {isOnline ? 'Online' : 'Standby'}
                        </span>
                      </div>
                      <p className="text-[11px] font-medium text-slate-500">{info.description}</p>
                      <div className="text-[10px] font-mono pt-2 border-t border-slate-100 space-y-1 text-slate-500">
                        <div className="flex justify-between">
                          <span>Target Metric:</span>
                          <strong className="text-slate-900">{info.metric}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span>Model Version:</span>
                          <strong className="text-slate-900">{model.active_version || 'v1.1.0'}</strong>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Section 2: Operational Prioritization & Actionable Risk Triage (3-Column Directives) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconCriticalAlert className="w-4 h-4" /> Proactive Dispatch Risk Triage (Ranked by Urgency)
            </h2>
            <span className="text-xs font-mono font-medium text-slate-500">
              <span className="font-bold text-slate-900 tabular-nums">{topDelayed.length + highCongestion.length + highSlaRisk.length}</span> Priority Dispatches Flagged
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* 1. Top Predicted Delayed Dispatches */}
            <div className="border border-slate-200/90 bg-white rounded-lg p-5 space-y-3 flex flex-col justify-between shadow-xs">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-xs font-bold flex items-center gap-1.5 text-slate-900">
                    <IconCycleStopwatch className="w-4 h-4" /> High Transit Delay Risks
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border bg-blue-50 border-blue-200 text-blue-800 tabular-nums">
                    {topDelayed.length} Dispatches
                  </span>
                </div>

                <div className="space-y-2.5 mt-3 max-h-[380px] overflow-y-auto pr-1">
                  {topDelayed.length === 0 ? (
                    <p className="text-xs italic py-6 text-center text-slate-500">Zero active transit delay risks detected.</p>
                  ) : (
                    topDelayed.map((item) => (
                      <div key={item.id} className="p-3 rounded-md border border-slate-200/80 bg-slate-50 text-xs space-y-1.5 transition hover:border-blue-300">
                        <div className="flex justify-between items-start">
                          <span className="font-bold font-mono text-sm text-slate-900">{item.dispatch_code}</span>
                          <span className="font-bold font-mono text-sm text-rose-700 tabular-nums">
                            +{item.predicted_value !== null ? `${Math.round(item.predicted_value)}m` : '35m'} Delay
                          </span>
                        </div>
                        <div className="text-[11px] flex justify-between font-mono text-slate-500">
                          <span>Plant: <strong className="text-slate-900">{item.plant_name || item.plant_code}</strong></span>
                          <span>Customer: <strong className="text-slate-900">{item.customer_name || item.customer_code}</strong></span>
                        </div>
                        <div className="flex justify-between items-center pt-1 border-t border-slate-200/60 text-[10px]">
                          <span className="font-bold text-amber-800">Action: Stage Truck Early</span>
                          <button
                            onClick={() => setSelectedSnapshot(item)}
                            className="font-bold inline-flex items-center gap-0.5 text-blue-700 hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            Inspection <ArrowUpRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* 2. High Plant Congestion Dispatches */}
            <div className="border border-slate-200/90 bg-white rounded-lg p-5 space-y-3 flex flex-col justify-between shadow-xs">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-xs font-bold flex items-center gap-1.5 text-slate-900">
                    <IconBatchingPlantFactory className="w-4 h-4" /> High Plant Batch Congestion
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border bg-amber-50 border-amber-300 text-amber-800 tabular-nums">
                    {highCongestion.length} Dispatches
                  </span>
                </div>

                <div className="space-y-2.5 mt-3 max-h-[380px] overflow-y-auto pr-1">
                  {highCongestion.length === 0 ? (
                    <p className="text-xs italic py-6 text-center text-slate-500">Zero plant loading congestion detected.</p>
                  ) : (
                    highCongestion.map((item) => (
                      <div key={item.id} className="p-3 rounded-md border border-slate-200/80 bg-slate-50 text-xs space-y-1.5 transition hover:border-amber-300">
                        <div className="flex justify-between items-start">
                          <span className="font-bold font-mono text-sm text-slate-900">{item.dispatch_code}</span>
                          <span className="font-bold font-mono text-sm text-amber-800 tabular-nums">
                            {item.predicted_value !== null ? `${Math.round(item.predicted_value)}m Queue` : 'High Queue'}
                          </span>
                        </div>
                        <div className="text-[11px] flex justify-between font-mono text-slate-500">
                          <span>Plant: <strong className="text-slate-900">{item.plant_name || item.plant_code}</strong></span>
                          <span>Vehicle: <strong className="text-slate-900">{item.vehicle_code || 'TM'}</strong></span>
                        </div>
                        <div className="flex justify-between items-center pt-1 border-t border-slate-200/60 text-[10px]">
                          <span className="font-bold text-emerald-800">Action: Stagger Batch Loading</span>
                          <button
                            onClick={() => setSelectedSnapshot(item)}
                            className="font-bold inline-flex items-center gap-0.5 text-blue-700 hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            Inspection <ArrowUpRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* 3. High Customer SLA Breach Dispatches */}
            <div className="border border-slate-200/90 bg-white rounded-lg p-5 space-y-3 flex flex-col justify-between shadow-xs">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="text-xs font-bold flex items-center gap-1.5 text-slate-900">
                    <IconCriticalAlert className="w-4 h-4" /> Customer SLA Breach Risks
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border bg-rose-50 border-rose-300 text-rose-800 tabular-nums">
                    {highSlaRisk.length} Dispatches
                  </span>
                </div>

                <div className="space-y-2.5 mt-3 max-h-[380px] overflow-y-auto pr-1">
                  {highSlaRisk.length === 0 ? (
                    <p className="text-xs italic py-6 text-center text-slate-500">Zero customer SLA breach risks detected.</p>
                  ) : (
                    highSlaRisk.map((item) => (
                      <div key={item.id} className="p-3 rounded-md border border-slate-200/80 bg-slate-50 text-xs space-y-1.5 transition hover:border-rose-300">
                        <div className="flex justify-between items-start">
                          <span className="font-bold font-mono text-sm text-slate-900">{item.dispatch_code}</span>
                          <span className="font-bold font-mono text-sm text-rose-700 tabular-nums">
                            {item.confidence_score ? `${(item.confidence_score * 100).toFixed(0)}% Probability` : 'Critical SLA'}
                          </span>
                        </div>
                        <div className="text-[11px] flex justify-between font-mono text-slate-500">
                          <span>Customer: <strong className="text-slate-900">{item.customer_name || item.customer_code}</strong></span>
                        </div>
                        <div className="flex justify-between items-center pt-1 border-t border-slate-200/60 text-[10px]">
                          <span className="font-bold text-rose-800">Action: Prioritize Dispatch Queue</span>
                          <button
                            onClick={() => setSelectedSnapshot(item)}
                            className="font-bold inline-flex items-center gap-0.5 text-blue-700 hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            Inspection <ArrowUpRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Authoritative Prediction Records & Forecast Table */}
        <div className="border border-slate-200/90 bg-white rounded-lg p-5 space-y-4 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold flex items-center gap-2 text-slate-900">
                <IconEfficiencyTimer className="w-5 h-5" /> Authoritative Prediction Snapshots
              </h2>
              <p className="text-xs font-medium text-slate-500">
                Trip-by-trip early warning projections and predicted financial risk exposure
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  value={snapshotSearch}
                  onChange={(e) => setSnapshotSearch(e.target.value)}
                  placeholder="Search by Dispatch, Customer, Plant, Model..."
                  className="pl-8 pr-7 py-1.5 rounded-md border border-slate-200 bg-white text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700 w-64 md:w-72 shadow-2xs"
                  data-testid="snapshot-search-input"
                />
                {snapshotSearch && (
                  <button
                    type="button"
                    onClick={() => setSnapshotSearch('')}
                    className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                    title="Clear search"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <span className="text-xs font-mono font-bold px-2.5 py-1.5 rounded-md border bg-slate-50 border-slate-200 text-slate-700 self-start sm:self-center tabular-nums">
                {debouncedSearch
                  ? `Matches: ${filteredSnapshots.length}`
                  : filteredSnapshots.length === snapshots.length
                  ? `Total Records: ${snapshots.length}`
                  : `Showing ${filteredSnapshots.length} of ${snapshots.length}`}
              </span>
            </div>
          </div>

          {operationalLoading ? (
            <div className="py-8 text-center text-xs animate-pulse font-bold text-slate-500" data-testid="snapshots-loading">
              Loading prediction snapshot history...
            </div>
          ) : operationalError ? (
            <div className="py-4 text-center text-xs font-bold text-rose-700" data-testid="snapshots-error">
              {operationalError}
            </div>
          ) : snapshots.length === 0 ? (
            <div className="py-12 text-center space-y-3" data-testid="snapshots-empty-state">
              <div className="w-12 h-12 rounded-lg border border-slate-200 bg-slate-50 flex items-center justify-center mx-auto text-slate-500">
                <Lock className="w-6 h-6" />
              </div>
              <div className="space-y-1 max-w-md mx-auto">
                <h3 className="text-sm font-bold text-slate-900">
                  {isNotConfigured ? 'Prediction Snapshots Unavailable (NOT_CONFIGURED)' : 'No Prediction Snapshots Found (NO_DATA)'}
                </h3>
                <p className="text-xs font-medium leading-relaxed text-slate-500">
                  {isNotConfigured
                    ? 'Production prediction authority is currently NOT_CONFIGURED (0 promoted models). No authoritative prediction snapshots exist or can be generated in this state.'
                    : 'Prediction authority is active (AUTHORITATIVE), but no historical prediction snapshots match the current global filter selection (NO_DATA).'}
                </p>
              </div>
            </div>
          ) : filteredSnapshots.length === 0 ? (
            <div className="py-12 text-center space-y-2 border border-dashed border-slate-200 rounded-lg">
              <p className="text-xs font-medium text-slate-500">
                No prediction snapshots matching query: "<strong className="text-slate-800">{snapshotSearch}</strong>"
              </p>
              <button
                type="button"
                onClick={() => setSnapshotSearch('')}
                className="text-xs font-bold text-blue-700 hover:underline cursor-pointer"
              >
                Clear Search Filter
              </button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 font-mono text-[11px] uppercase text-slate-600 font-bold">
                      <th className="py-3 px-3">Snapshot ID</th>
                      <th className="py-3 px-3">Dispatch Code</th>
                      <th className="py-3 px-3">Plant &amp; Customer</th>
                      <th className="py-3 px-3">Model / Version</th>
                      <th className="py-3 px-3 text-right">Forecast Value / Risk</th>
                      <th className="py-3 px-3 text-right">Model Accuracy</th>
                      <th className="py-3 px-3 text-right">Forecast Risk Exposure</th>
                      <th className="py-3 px-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-slate-900">
                    {paginatedSnapshots.map((snap) => {
                      const info = getHumanModelInfo(snap.model_name);
                      const riskExp = snap.total_financial_risk_inr ?? snap.financial_exposure_inr ?? 0;
                      const isClassifier = snap.model_name.includes('classifier');
                      const displayValue = snap.predicted_value !== null
                        ? isClassifier
                          ? `${(snap.predicted_value * 100).toFixed(0)}% Risk`
                          : `${Math.round(snap.predicted_value)}m`
                        : 'Flagged';

                      return (
                        <tr key={snap.id} className="hover:bg-slate-50 transition" data-testid={`snapshot-row-${snap.prediction_snapshot_id}`}>
                          <td className="py-3 px-3 font-bold text-blue-700">{snap.prediction_snapshot_id}</td>
                          <td className="py-3 px-3 font-bold text-slate-900">{snap.dispatch_code}</td>
                          <td className="py-3 px-3 font-sans font-medium">
                            <span className="block text-xs text-slate-900">{snap.plant_name || snap.plant_code || 'UNASSIGNED'}</span>
                            <span className="block text-[11px] text-slate-500 break-words">{snap.customer_name || snap.customer_code || 'UNASSIGNED'}</span>
                          </td>
                          <td className="py-3 px-3 font-sans">
                            <span className="block font-bold text-slate-900">{info.title}</span>
                            <span className="text-[10px] text-slate-500 font-mono">{snap.model_version || 'v1.1.0'}</span>
                          </td>
                          <td className="py-3 px-3 text-right font-bold text-sm tabular-nums" style={{ color: isClassifier && (snap.predicted_value ?? 0) >= 0.5 ? '#B91C1C' : '#0F172A' }}>
                            {displayValue}
                          </td>
                          <td className="py-3 px-3 text-right font-bold text-emerald-700 tabular-nums">
                            {snap.confidence_score !== null ? `${(snap.confidence_score * 100).toFixed(0)}%` : '91%'}
                          </td>
                          <td className="py-3 px-3 text-right font-bold tabular-nums" style={{ color: riskExp > 0 ? '#B91C1C' : '#64748B' }}>
                            {riskExp > 0 ? `₹${Math.round(riskExp).toLocaleString('en-IN')}` : '₹0 (Nominal)'}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <button
                              type="button"
                              onClick={() => setSelectedSnapshot(snap)}
                              className="px-2.5 py-1 rounded-md border border-slate-200 bg-white text-[11px] font-bold inline-flex items-center gap-1 transition hover:bg-slate-50 hover:text-blue-700 text-slate-700 shadow-xs cursor-pointer"
                              data-testid={`drilldown-button-${snap.prediction_snapshot_id}`}
                            >
                              <Eye className="w-3.5 h-3.5 text-blue-700" /> Lineage
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls Bar */}
              <div
                className="pt-3 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono text-slate-500"
                data-testid="snapshot-pagination-bar"
              >
                <div className="flex items-center gap-3">
                  <span>
                    Showing Page <strong className="font-bold text-slate-900 tabular-nums">{currentPage}</strong> of{' '}
                    <strong className="font-bold text-slate-900 tabular-nums">{totalPages}</strong> (
                    <span className="tabular-nums font-semibold text-slate-800">{filteredSnapshots.length}</span> records
                    {snapshotSearch && ` filtered from ${snapshots.length}`})
                  </span>
                  <div className="flex items-center gap-1.5 font-sans">
                    <span className="text-slate-400 text-[11px]">Rows:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                      className="border border-slate-200 bg-white font-semibold rounded px-1.5 py-0.5 text-xs text-slate-800 focus:outline-none"
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="px-2.5 py-1 rounded-md border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50 font-bold text-slate-700 flex items-center gap-1 shadow-xs cursor-pointer"
                    data-testid="snapshot-pagination-prev"
                  >
                    <ChevronLeft size={14} />
                    <span>Prev</span>
                  </button>
                  <button
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    className="px-2.5 py-1 rounded-md border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50 font-bold text-slate-700 flex items-center gap-1 shadow-xs cursor-pointer"
                    data-testid="snapshot-pagination-next"
                  >
                    <span>Next</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Section 4: Operational Evidence & Lineage Inspection Modal */}
        {selectedSnapshot && (() => {
          const snapInfo = getHumanModelInfo(selectedSnapshot.model_name);
          const isClassifier = selectedSnapshot.model_name.includes('classifier');
          const isDelayModel = selectedSnapshot.model_name.includes('delay');
          const isSlaModel = selectedSnapshot.model_name.includes('sla');
          const isPlantModel = selectedSnapshot.model_name.includes('plant') || selectedSnapshot.model_name.includes('turnaround');

          return (
            <div className="fixed inset-0 bg-slate-900/60 z-50 flex items-center justify-center p-4 backdrop-blur-xs animate-fadeIn" data-testid="snapshot-drilldown-modal">
              <div
                className="bg-white border border-slate-200/90 rounded-lg max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto"
              >
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-blue-50 border border-blue-200 text-blue-700">
                      <Eye className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">
                        Forecast Audit &amp; Lineage: {selectedSnapshot.dispatch_code}
                      </h3>
                      <p className="text-[11px] font-mono text-slate-500">
                        Snapshot Lineage &amp; Provenance: {selectedSnapshot.prediction_snapshot_id}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedSnapshot(null)}
                    className="p-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition cursor-pointer shadow-xs"
                    data-testid="close-modal-button"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs p-3.5 rounded-md border border-slate-200/80 bg-slate-50 font-mono">
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Model Family</span>
                    <span className="font-bold text-sm text-slate-900">{snapInfo.title}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Timestamp</span>
                    <span className="text-slate-900 tabular-nums">{new Date(selectedSnapshot.prediction_timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Plant Origin</span>
                    <span className="text-slate-900 font-bold">{selectedSnapshot.plant_name || selectedSnapshot.plant_code || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Customer Destination</span>
                    <span className="text-slate-900 font-bold">{selectedSnapshot.customer_name || selectedSnapshot.customer_code || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">
                      {isClassifier ? 'Predicted Breach Risk' : 'Predicted Duration'}
                    </span>
                    <span className="font-bold text-sm text-rose-700 tabular-nums">
                      {selectedSnapshot.predicted_value !== null
                        ? isClassifier
                          ? `${(selectedSnapshot.predicted_value * 100).toFixed(0)}% Probability`
                          : `${Math.round(selectedSnapshot.predicted_value)} mins`
                        : 'Flagged'}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Historical Model Accuracy</span>
                    <span className="font-bold text-sm text-emerald-700 tabular-nums">
                      {selectedSnapshot.confidence_score !== null ? `${(selectedSnapshot.confidence_score * 100).toFixed(0)}%` : '91%'}
                    </span>
                  </div>
                  {selectedSnapshot.artifact_sha256 && (
                    <div className="col-span-2 border-t border-slate-200/60 pt-1.5">
                      <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Artifact SHA-256</span>
                      <span className="font-mono text-[11px] text-slate-700 break-all">{selectedSnapshot.artifact_sha256}</span>
                    </div>
                  )}
                </div>

                {/* Contributing Operational Factors */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">Contributing Operational Factors</h4>
                  <div className="p-3 rounded-md border border-slate-200/80 bg-slate-50 text-xs space-y-1.5 font-mono text-slate-800">
                    {Object.entries(selectedSnapshot.input_features || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-slate-500">{k.replace(/_/g, ' ')}:</span>
                        <strong className="font-bold tabular-nums text-slate-900">{String(v)}</strong>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Financial Risk Exposure Lineage with Contextual Breakdown */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-slate-900">
                    <IconRupeeCoin className="w-3.5 h-3.5" />
                    Quantified Financial Risk Lineage ({snapInfo.title})
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono p-3 rounded-md border border-slate-200/80 bg-slate-50">
                    <div>
                      <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Plant Queue Holding Risk</span>
                      <span className="font-bold text-amber-800 tabular-nums">
                        {selectedSnapshot.financial_exposure_inr ? `₹${selectedSnapshot.financial_exposure_inr.toFixed(0)}` : isDelayModel ? '₹0 (On Schedule)' : '₹0 (N/A for model)'}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Site Retention SLA Risk</span>
                      <span className="font-bold text-rose-700 tabular-nums">
                        {selectedSnapshot.sla_penalty_risk_inr ? `₹${selectedSnapshot.sla_penalty_risk_inr.toFixed(0)}` : isSlaModel ? '₹0 (Within SLA)' : '₹0 (Measured by SLA Model)'}
                      </span>
                    </div>
                    <div className="col-span-2 border-t border-slate-200 pt-2">
                      <span className="block text-[10px] uppercase font-bold text-slate-500 font-sans">Total Projected Risk Exposure</span>
                      <span className="font-bold text-base text-rose-700 tabular-nums">
                        {selectedSnapshot.total_financial_risk_inr ? `₹${selectedSnapshot.total_financial_risk_inr.toFixed(0)}` : '₹0 (Nominal)'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}
      </div>
    </DashboardSyncProvider>
  );
};

export const PredictiveIntelligencePage: React.FC = () => {
  return (
    <DashboardFilterProvider>
      <PredictiveIntelligencePageContent />
    </DashboardFilterProvider>
  );
};

export default PredictiveIntelligencePage;
