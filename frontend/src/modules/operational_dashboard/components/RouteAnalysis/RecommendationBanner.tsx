import React from 'react';
import { CheckCircle2, AlertTriangle, Info, Clock, ArrowRight, ShieldAlert } from 'lucide-react';
import { RouteAnalysisSynthesisResult, SynthesisDecisionOutcome } from './routeAnalysis.types';

interface RecommendationBannerProps {
  result: RouteAnalysisSynthesisResult;
}

export const RecommendationBanner: React.FC<RecommendationBannerProps> = ({ result }) => {
  const {
    recommendation_status,
    primary_case_category,
    minutes_saved,
    is_traffic_override,
    decision_reason_summary,
    recommended_plant_name,
    recommended_plant_code,
    current_source_plant_name,
    current_source_plant_code,
    is_google_fresh,
    is_google_stale_cache,
    google_cache_age_seconds,
    failure_reason_code,
  } = result;

  // Determine state styling
  const isAltRecommended = recommendation_status === 'RECOMMEND_ALTERNATIVE';
  const isCurrentRecommended = recommendation_status === 'RECOMMEND_CURRENT_SOURCE';
  const isNoClearDiff = recommendation_status === 'NO_CLEAR_DIFFERENCE';
  const isHistoricalOnly = recommendation_status === 'HISTORICAL_COMPARISON_ONLY';
  const isLiveRouteOnly = recommendation_status === 'LIVE_ROUTE_ONLY';
  const isMissingData = recommendation_status === 'LOCATION_DATA_MISSING' || failure_reason_code === 'LOCATION_DATA_MISSING' || primary_case_category?.startsWith('C11');
  const isNoRec = recommendation_status === 'NO_RECOMMENDATION' || primary_case_category?.startsWith('C9') || isMissingData;

  let bgClass = 'bg-blue-50/80 border-blue-200 text-blue-900';
  let badgeClass = 'bg-blue-100 text-blue-800 border-blue-200';
  let icon = <Info className="w-5 h-5 text-blue-600 shrink-0" />;
  let title = 'Route Analysis Recommendation';

  if (isAltRecommended) {
    bgClass = 'bg-emerald-50/90 border-emerald-300 text-emerald-950 shadow-2xs';
    badgeClass = 'bg-emerald-100 text-emerald-800 border-emerald-200';
    icon = <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />;
    title = is_traffic_override ? 'RECOMMEND ALTERNATIVE PLANT (Traffic Override)' : 'RECOMMEND ALTERNATIVE PLANT';
  } else if (isCurrentRecommended) {
    bgClass = 'bg-blue-50/90 border-blue-200 text-blue-950 shadow-2xs';
    badgeClass = 'bg-blue-100 text-blue-800 border-blue-200';
    icon = <CheckCircle2 className="w-5 h-5 text-blue-600 shrink-0" />;
    title = is_traffic_override ? 'RECOMMEND CURRENT APPROVED PLANT (Traffic Override)' : 'RECOMMEND CURRENT APPROVED PLANT';
  } else if (isNoClearDiff) {
    bgClass = 'bg-amber-50/80 border-amber-200 text-amber-900';
    badgeClass = 'bg-amber-100 text-amber-800 border-amber-200';
    icon = <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />;
    title = 'NO CLEAR ROUTE ADVANTAGE — RETAIN CURRENT PLANT';
  } else if (isHistoricalOnly) {
    bgClass = 'bg-orange-50/80 border-orange-200 text-orange-900';
    badgeClass = 'bg-orange-100 text-orange-800 border-orange-200';
    icon = <Clock className="w-5 h-5 text-orange-600 shrink-0" />;
    title = 'HISTORICAL COMPARISON ONLY (Live Traffic Unavailable)';
  } else if (isLiveRouteOnly) {
    bgClass = 'bg-sky-50/80 border-sky-200 text-sky-900';
    badgeClass = 'bg-sky-100 text-sky-800 border-sky-200';
    icon = <Info className="w-5 h-5 text-sky-600 shrink-0" />;
    title = 'LIVE ROUTE ESTIMATE ONLY (Insufficient Historical Data)';
  } else if (isMissingData) {
    bgClass = 'bg-rose-50/80 border-rose-200 text-rose-900';
    badgeClass = 'bg-rose-100 text-rose-800 border-rose-200';
    icon = <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />;
    title = 'LOCATION DATA MISSING — UPDATE IN ERP / MASTER DATA';
  } else if (isNoRec) {
    bgClass = 'bg-slate-50 border-slate-200 text-slate-800';
    badgeClass = 'bg-slate-100 text-slate-700 border-slate-200';
    icon = <AlertTriangle className="w-5 h-5 text-slate-500 shrink-0" />;
    title = 'NO RECOMMENDATION AVAILABLE';
  }

  const formattedCase = (primary_case_category || 'N/A').replace(/_/g, ' ');

  return (
    <div data-testid="recommendation-banner" className={`p-4 rounded-lg border transition-all ${bgClass}`}>
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Recommendation Title & Core Statement */}
        <div className="flex items-start gap-3">
          <div className="mt-0.5">{icon}</div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-sm md:text-base tracking-tight">{title}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase tracking-wider ${badgeClass}`}>
                Case: {formattedCase}
              </span>
            </div>

            <p className="text-xs md:text-sm font-medium leading-relaxed max-w-4xl text-slate-700">
              {decision_reason_summary}
            </p>
          </div>
        </div>

        {/* Right: Key Decision Delta Callout Card */}
        <div className="flex items-center gap-3 shrink-0 self-end lg:self-center">
          {!isNoRec && !isMissingData && minutes_saved !== null && minutes_saved !== undefined && minutes_saved > 0 && (
            <div className="text-right px-3.5 py-1.5 rounded-lg bg-white border border-slate-200/90 shadow-2xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Route Advantage</div>
              <div className="text-lg font-extrabold text-emerald-700 font-mono tabular-nums">
                +{minutes_saved.toFixed(1)} <span className="text-xs font-semibold font-sans">mins</span>
              </div>
            </div>
          )}

          {!isNoRec && !isMissingData && recommended_plant_name && (
            <div className="px-3.5 py-1.5 rounded-lg bg-white border border-slate-200/90 shadow-2xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Recommended Plant</div>
              <div className="text-sm font-extrabold text-slate-900">
                {recommended_plant_name}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Freshness & Stale Cache Warning Footer if applicable */}
      {is_google_stale_cache && (
        <div className="mt-3 pt-3 border-t border-amber-200/60 flex items-center gap-2 text-xs font-medium text-amber-800">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            Google traffic payload was served from cache ({Math.round(google_cache_age_seconds || 0)}s age). Stale traffic is displayed for reference only and cannot produce a current recommendation.
          </span>
        </div>
      )}
    </div>
  );
};
