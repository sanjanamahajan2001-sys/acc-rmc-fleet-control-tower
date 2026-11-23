import React from 'react';
import { DecisionSummaryCards, DecisionSummary } from './DecisionSummaryCards';
import { RecommendationTable, RecommendationRow } from './RecommendationTable';
import { RecommendationCardGroup, DecisionInsightCard } from './RecommendationCardGroup';

export interface DecisionIntelligenceContainerData {
  summary: DecisionSummary;
  recommendations: RecommendationRow[];
  insights: DecisionInsightCard[];
}

interface DecisionIntelligenceContainerProps {
  data: DecisionIntelligenceContainerData | null;
  loading?: boolean;
}

export const DecisionIntelligenceContainer: React.FC<DecisionIntelligenceContainerProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 animate-pulse space-y-4 shadow-xl">
        <div className="h-4 w-72 bg-slate-800 rounded" />
        <div className="h-40 w-full bg-slate-800/80 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 space-y-6 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h2 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          OPERATIONAL DECISION INTELLIGENCE & RECOMMENDED ACTIONS
        </h2>
        <span className="text-[11px] font-mono text-slate-500 font-bold uppercase">Workstream 2.9 Active</span>
      </div>

      {/* 1. Decision Intelligence Summary Cards */}
      <DecisionSummaryCards summary={data.summary} />

      {/* 2. Ranked Recommendation Actions Table */}
      <RecommendationTable recommendations={data.recommendations || []} />

      {/* 3. Strategic Decision Cards */}
      <RecommendationCardGroup insights={data.insights || []} />
    </div>
  );
};
