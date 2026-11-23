import React from 'react';
import { PerformanceSummaryCards, PerformanceSummary } from './PerformanceSummaryCards';
import { DelayDistributionChart, DelayCategory } from './DelayDistributionChart';
import { OperationalInsightsPanel, InsightItem } from './OperationalInsightsPanel';

export interface SitePerformanceContainerData {
  summary: PerformanceSummary;
  delay_distribution: DelayCategory[];
  insights: InsightItem[];
}

interface SitePerformanceContainerProps {
  data: SitePerformanceContainerData | null;
  loading?: boolean;
}

export const SitePerformanceContainer: React.FC<SitePerformanceContainerProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 animate-pulse space-y-4 shadow-xl">
        <div className="h-4 w-56 bg-slate-800 rounded" />
        <div className="h-32 w-full bg-slate-800/80 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 space-y-6 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h2 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          SITE PERFORMANCE INTELLIGENCE & SLA INSIGHTS
        </h2>
        <span className="text-[11px] font-mono text-slate-500 font-bold uppercase">Workstream 2.7 Active</span>
      </div>

      {/* 1. SLA Performance Summary Cards */}
      <PerformanceSummaryCards summary={data.summary} />

      {/* 2. Operational Delay Severity Distribution */}
      <DelayDistributionChart delays={data.delay_distribution || []} />

      {/* 3. Operational Insights & Performance Health Panel */}
      <OperationalInsightsPanel insights={data.insights || []} />
    </div>
  );
};
