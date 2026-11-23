import React, { useState } from 'react';
import { useGoogleApiUsage } from '../../hooks/useRouteAnalysis';
import {
  Globe,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  HelpCircle,
  TrendingDown,
  Calendar,
  Zap,
  Info,
  X,
  Layers,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';

export const GoogleApiUsageIndicator: React.FC = () => {
  const { data, isLoading, isError, refetch } = useGoogleApiUsage();
  const [showModal, setShowModal] = useState<boolean>(false);

  const usage = data?.data;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 animate-pulse text-xs text-slate-400">
        <Globe className="w-3.5 h-3.5" />
        <span>Loading API Quota...</span>
      </div>
    );
  }

  if (isError || !usage) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
        <Globe className="w-3.5 h-3.5 text-slate-400" />
        <span>Google Maps Quota: Telemetry Standby</span>
      </div>
    );
  }

  const {
    total_billable_requests_month,
    cached_requests_saved_month,
    monthly_allowance_limit,
    remaining_allowance,
    usage_percentage,
    status,
    is_api_configured,
    billing_cycle_start,
    billing_cycle_end,
    last_queried_at,
    estimated_cost_usd,
  } = usage;

  const totalCalculatedOps = total_billable_requests_month + cached_requests_saved_month;
  const cacheEfficiencyPct =
    totalCalculatedOps > 0 ? Math.round((cached_requests_saved_month / totalCalculatedOps) * 100) : 0;

  // Status configuration
  let statusBadgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  let statusIcon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />;
  let progressBarColor = 'bg-emerald-500';
  let statusLabel = 'HEALTHY';

  if (!is_api_configured || status === 'UNCONFIGURED') {
    statusBadgeColor = 'bg-slate-100 text-slate-700 border-slate-300';
    statusIcon = <HelpCircle className="w-3.5 h-3.5 text-slate-500" />;
    progressBarColor = 'bg-slate-400';
    statusLabel = 'NO API KEY';
  } else if (status === 'EXCEEDED' || usage_percentage >= 100) {
    statusBadgeColor = 'bg-rose-50 text-rose-700 border-rose-200';
    statusIcon = <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />;
    progressBarColor = 'bg-rose-500';
    statusLabel = 'CAP EXCEEDED';
  } else if (status === 'CRITICAL' || usage_percentage >= 90) {
    statusBadgeColor = 'bg-rose-50 text-rose-700 border-rose-200';
    statusIcon = <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />;
    progressBarColor = 'bg-rose-500';
    statusLabel = 'CRITICAL (>90%)';
  } else if (status === 'WARNING' || usage_percentage >= 70) {
    statusBadgeColor = 'bg-amber-50 text-amber-700 border-amber-200';
    statusIcon = <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />;
    progressBarColor = 'bg-amber-500';
    statusLabel = 'WARNING (>70%)';
  }

  const formattedCycleStart = billing_cycle_start
    ? new Date(billing_cycle_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : '1st of month';
  const formattedCycleEnd = billing_cycle_end
    ? new Date(billing_cycle_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : 'Month end';

  return (
    <>
      {/* Compact Ribbon Widget */}
      <div
        onClick={() => setShowModal(true)}
        className="flex items-center gap-3 px-3 py-1.5 rounded-md bg-slate-50 hover:bg-slate-100 border border-slate-200/90 transition-all cursor-pointer shadow-2xs group"
        title="Click to view full Google Maps API usage breakdown and allowance metrics"
      >
        <div className="flex items-center gap-1.5">
          <Globe className="w-4 h-4 text-blue-700 group-hover:scale-105 transition-transform" />
          <span className="text-[11px] font-bold text-slate-700">Google Routes API:</span>
        </div>

        {/* Progress Bar Container */}
        <div className="flex items-center gap-2">
          <div className="w-20 sm:w-28 h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${progressBarColor} transition-all duration-500 rounded-full`}
              style={{ width: `${Math.min(100, usage_percentage)}%` }}
            />
          </div>
          <span className="text-[11px] font-mono font-bold text-slate-800 tabular-nums">
            {usage_percentage}%
          </span>
        </div>

        {/* Remaining Allowance Badge */}
        <div className={`hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold ${statusBadgeColor}`}>
          {statusIcon}
          <span className="tabular-nums">{remaining_allowance.toLocaleString()} calls left</span>
        </div>

        {/* Info Trigger Button */}
        <div className="p-0.5 rounded-md text-slate-400 group-hover:text-blue-700 transition-colors">
          <Info className="w-3.5 h-3.5" />
        </div>
      </div>

      {/* Usage & Allowance Breakdown Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4 animate-fade-in">
          <div
            className="bg-white rounded-lg shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-700 text-white shadow-2xs">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Google Maps &amp; Routes API Allowance
                  </h3>
                  <p className="text-xs text-slate-500">
                    Monthly billing cycle telemetry &amp; cost optimization
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-3.5 text-xs text-slate-700">
              {/* Top Banner: Status & Percentage */}
              <div className="p-3.5 rounded-lg border border-slate-200/90 bg-slate-50/70 flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-600">Cycle Status:</span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border uppercase flex items-center gap-1 ${statusBadgeColor}`}>
                      {statusIcon}
                      {statusLabel}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-semibold text-slate-400">Free Tier Allowance</span>
                    <p className="font-mono font-bold text-slate-900 text-sm tabular-nums">
                      {total_billable_requests_month.toLocaleString()} / {monthly_allowance_limit.toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1">
                  <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${progressBarColor} transition-all duration-500 rounded-full`}
                      style={{ width: `${Math.min(100, usage_percentage)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono tabular-nums">
                    <span>{usage_percentage}% Consumed</span>
                    <span>{remaining_allowance.toLocaleString()} calls remaining</span>
                  </div>
                </div>
              </div>

              {/* Metric Cards Grid */}
              <div className="grid grid-cols-2 gap-3">
                {/* Outgoing API Requests */}
                <div className="p-3 rounded-md border border-slate-200/90 bg-white space-y-1 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-slate-600 font-semibold text-[11px]">
                    <Zap className="w-3.5 h-3.5 text-blue-700" />
                    <span>Billable Calls (Month)</span>
                  </div>
                  <p className="text-base font-bold font-mono text-slate-900 tabular-nums">
                    {total_billable_requests_month.toLocaleString()}
                  </p>
                  <p className="text-[10px] text-slate-400">
                    Direct Google Routes API requests
                  </p>
                </div>

                {/* Cached Requests Saved */}
                <div className="p-3 rounded-md border border-emerald-200/80 bg-emerald-50/40 space-y-1 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-emerald-700 font-semibold text-[11px]">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Cache-Saved Calls</span>
                  </div>
                  <p className="text-base font-bold font-mono text-emerald-800 tabular-nums">
                    {cached_requests_saved_month.toLocaleString()}
                  </p>
                  <p className="text-[10px] text-emerald-600 font-medium">
                    {cacheEfficiencyPct}% caching cost reduction
                  </p>
                </div>

                {/* Billing Cycle */}
                <div className="p-3 rounded-md border border-slate-200/90 bg-white space-y-1 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-slate-600 font-semibold text-[11px]">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Current Billing Cycle</span>
                  </div>
                  <p className="text-xs font-bold text-slate-800">
                    {formattedCycleStart} – {formattedCycleEnd}
                  </p>
                  <p className="text-[10px] text-slate-400">
                    Resets automatically on 1st of month
                  </p>
                </div>

                {/* Estimated Incurred Cost */}
                <div className="p-3 rounded-md border border-slate-200/90 bg-white space-y-1 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-slate-600 font-semibold text-[11px]">
                    <TrendingDown className="w-3.5 h-3.5 text-slate-500" />
                    <span>Estimated Overage Cost</span>
                  </div>
                  <p className="text-base font-bold font-mono text-slate-900 tabular-nums">
                    ${estimated_cost_usd.toFixed(2)} USD
                  </p>
                  <p className="text-[10px] text-slate-400">
                    $0.00 within standard $200 free credit
                  </p>
                </div>
              </div>

              {/* Informational Guidance Note */}
              <div className="p-3 rounded-md bg-blue-50/60 border border-blue-200/70 flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-blue-700 shrink-0 mt-0.5" />
                <div className="text-[11px] text-blue-950 space-y-0.5">
                  <p className="font-bold">Authoritative Telemetry &amp; Safety</p>
                  <p className="text-slate-600 leading-relaxed">
                    Calls are deduplicated across plant corridors and cached (300s TTL) to maximize free-tier mileage. API server keys remain strictly isolated on the backend.
                  </p>
                </div>
              </div>

              {last_queried_at && (
                <p className="text-[10px] text-slate-400 text-center font-mono">
                  Last Outgoing API Call: {new Date(last_queried_at).toLocaleString()}
                </p>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-3.5 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
              <button
                type="button"
                onClick={() => refetch()}
                className="px-3 py-1.5 rounded-md text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition"
              >
                Refresh Metrics
              </button>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-1.5 rounded-md text-xs font-bold bg-blue-700 text-white hover:bg-blue-800 transition shadow-2xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
