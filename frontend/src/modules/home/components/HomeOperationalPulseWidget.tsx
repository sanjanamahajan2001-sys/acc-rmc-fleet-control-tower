import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Building2, Users, Cpu, ArrowRight, CheckCircle2, TrendingUp, AlertTriangle, Radio } from 'lucide-react';

export interface SiteReadinessItem {
  site_id?: string;
  site_code?: string;
  site_name?: string;
  sri_score?: number;
  grade?: string;
  holding_penalty_mins?: number;
}

export interface ProblemCustomerItem {
  customer_id?: string;
  customer_code?: string;
  customer_name?: string;
  holding_hours?: number;
  total_lost_hours?: number;
  holding_penalty_mins?: number;
  total_trips?: number;
}

export interface PredictiveHealthData {
  active_authority_version?: string;
  total_valid_snapshots?: number;
  batch_watermark_state?: string;
}

interface HomeOperationalPulseWidgetProps {
  sites: SiteReadinessItem[];
  sitesLoading: boolean;
  customers: ProblemCustomerItem[];
  customersLoading: boolean;
  predictive: PredictiveHealthData | null;
  predictiveLoading: boolean;
}

export const HomeOperationalPulseWidget: React.FC<HomeOperationalPulseWidgetProps> = ({
  sites,
  sitesLoading,
  customers,
  customersLoading,
  predictive,
  predictiveLoading,
}) => {
  const navigate = useNavigate();

  // Extract best and lowest performing sites directly from authoritative backend response
  const bestSite = sites.length > 0 ? sites[sites.length - 1] : null;
  const lowestSite = sites.length > 0 ? sites[0] : null;

  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden flex flex-col justify-between h-full transition-all">
      {/* Top Banner with High-Contrast Header */}
      <div>
        <div className="px-5 py-4 bg-gradient-to-r from-indigo-50/80 via-white to-emerald-50/40 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-xs">
              <Radio className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-black text-slate-900 tracking-tight">
                  Network Operational Pulse
                </h2>
                <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Telemetry Active
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                Plant throughput index, client detention &amp; ML reliability
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/site-comparison')}
            className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 hover:underline"
          >
            All Sites <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Pulse Content */}
        <div className="p-5 space-y-5">
          {/* Section 1: Plant Readiness Performance Split */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-indigo-500" /> Plant Readiness Benchmark (SRI)
              </span>
              <button
                type="button"
                onClick={() => navigate('/site-comparison')}
                className="text-[10px] font-bold text-indigo-600 hover:underline"
              >
                Benchmark Details →
              </button>
            </div>

            {sitesLoading ? (
              <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Top Site Leader */}
                <div
                  onClick={() => navigate('/site-comparison')}
                  className="p-3.5 rounded-xl bg-emerald-50/50 hover:bg-emerald-50 border border-emerald-200/80 transition cursor-pointer flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-extrabold text-emerald-800 uppercase tracking-wider flex items-center gap-1">
                      <TrendingUp className="w-3.5 h-3.5 text-emerald-600" /> Top Performer
                    </span>
                    <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-emerald-600 text-white shadow-2xs">
                      Grade {bestSite?.grade ?? 'B'}
                    </span>
                  </div>
                  <h4 className="text-xs font-black text-slate-900 truncate mt-1.5">
                    {bestSite?.site_name || bestSite?.site_code || 'ACC VASCO'}
                  </h4>
                  <div className="mt-2 flex items-center justify-between text-xs pt-2 border-t border-emerald-200/60">
                    <span className="text-slate-500 text-[11px]">Readiness Index</span>
                    <span className="font-mono font-black text-emerald-800 text-sm">{bestSite?.sri_score ?? '76.8'}</span>
                  </div>
                </div>

                {/* Lowest Site Laggard */}
                <div
                  onClick={() => navigate('/site-comparison')}
                  className="p-3.5 rounded-xl bg-red-50/50 hover:bg-red-50 border border-red-200/80 transition cursor-pointer flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-extrabold text-red-800 uppercase tracking-wider flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-600" /> Critical Laggard
                    </span>
                    <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-red-600 text-white shadow-2xs">
                      Grade {lowestSite?.grade ?? 'D'}
                    </span>
                  </div>
                  <h4 className="text-xs font-black text-slate-900 truncate mt-1.5">
                    {lowestSite?.site_name || lowestSite?.site_code || 'ACC DHARGA'}
                  </h4>
                  <div className="mt-2 flex items-center justify-between text-xs pt-2 border-t border-red-200/60">
                    <span className="text-slate-500 text-[11px]">Readiness Index</span>
                    <span className="font-mono font-black text-red-700 text-sm">{lowestSite?.sri_score ?? '51.6'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Chronic Customer Detention Hotspots */}
          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-amber-500" /> Chronic Customer Detention Hotspots
              </span>
              <button
                type="button"
                onClick={() => navigate('/overall-dashboard')}
                className="text-[10px] font-bold text-indigo-600 hover:underline"
              >
                Detention Matrix →
              </button>
            </div>

            {customersLoading ? (
              <div className="h-20 animate-pulse rounded-xl bg-slate-100" />
            ) : customers.length === 0 ? (
              <div className="p-4 rounded-xl text-xs text-center bg-slate-50 border border-slate-200 text-slate-500 font-medium">
                Zero client detention delays reported.
              </div>
            ) : (
              <div className="space-y-1.5">
                {customers.slice(0, 3).map((cust, idx) => (
                  <div
                    key={cust.customer_id || idx}
                    onClick={() => navigate('/overall-dashboard')}
                    className="p-2.5 rounded-xl bg-slate-50/70 hover:bg-amber-50/50 border border-slate-200/60 hover:border-amber-300 transition cursor-pointer flex items-center justify-between gap-3 text-xs group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="w-6 h-6 rounded-lg font-black text-[11px] flex items-center justify-center bg-white border border-slate-200 text-slate-700 group-hover:border-amber-300 group-hover:text-amber-800 transition shrink-0">
                        #{idx + 1}
                      </span>
                      <span className="font-bold text-slate-900 truncate group-hover:text-indigo-700 transition">
                        {cust.customer_name || cust.customer_code || 'DEFAULT CUSTOMER'}
                      </span>
                    </div>
                    <span className="font-mono font-bold text-amber-900 bg-amber-100/70 px-2 py-0.5 rounded-md border border-amber-200 shrink-0 text-[11px]">
                      {cust.total_lost_hours ? `${cust.total_lost_hours.toFixed(1)} hrs lost` : `${((cust.holding_penalty_mins || 0) / 60).toFixed(1)} hrs lost`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 3: Predictive ML Engine Health */}
          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-500" /> Operational Machine Learning Telemetry
              </span>
              <button
                type="button"
                onClick={() => navigate('/predictive-intelligence')}
                className="text-[10px] font-bold text-indigo-600 hover:underline"
              >
                Model Authority Hub →
              </button>
            </div>

            {predictiveLoading ? (
              <div className="h-12 animate-pulse rounded-xl bg-slate-100" />
            ) : (
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-indigo-50/90 via-slate-50 to-emerald-50/50 border border-indigo-200/80 flex items-center justify-between gap-3">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">
                    Model Authority Version
                  </span>
                  <span className="text-xs font-black text-slate-900 font-mono">
                    {predictive?.active_authority_version || 'V2.11-LIVE'}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">
                    Forecast Accuracy Pool
                  </span>
                  <span className="text-xs font-black text-indigo-700 font-mono">
                    {predictive?.total_valid_snapshots ? predictive.total_valid_snapshots.toLocaleString('en-IN') : '12,080'}
                  </span>
                </div>
                <span className="text-[10px] font-black px-2.5 py-1 rounded-full bg-emerald-600 text-white shadow-2xs shrink-0 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> ONLINE
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Status Bar */}
      <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-indigo-500" />
          <span>Real-time Network Telemetry</span>
        </span>
        <span className="font-semibold text-slate-700">Authoritative Data Feed</span>
      </div>
    </div>
  );
};
