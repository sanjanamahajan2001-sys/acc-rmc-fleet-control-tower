import React from 'react';
import { Sparkles, Clock, AlertTriangle, ShieldAlert, ArrowUpRight, CheckCircle2, TrendingUp } from 'lucide-react';
import { IconSupervisorDirectives, IconQualityAward } from '../../../components/icons/LinealColorIcons';
import { KPICard } from '../../../components/common/KPICard';

export interface DecisionSummaryCounts {
  active_recommendations: number;
  high_priority_issues: number;
  estimated_delay_reduction_mins: number;
  estimated_sla_recovery_pct: number;
  fleet_efficiency_opportunity_pct: number;
}

export interface RecommendationItem {
  recommendation_id: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  recommendation_text: string;
  underlying_reason: string;
  affected_plant: string;
  affected_vehicle?: string | null;
  expected_impact: string;
  confidence_pct: number;
  status: string;
}

export interface DecisionInsightItem {
  title: string;
  category: string;
  action_type: string;
  description: string;
  urgency: 'Immediate' | 'Scheduled' | 'Proactive';
}

export interface OperationalDecisionRecommendationData {
  summary: DecisionSummaryCounts;
  recommendations: RecommendationItem[];
  insights: DecisionInsightItem[];
  calculation_status: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculation_notes: string;
}

interface OperationalDecisionRecommendationsSectionProps {
  data: OperationalDecisionRecommendationData | null;
}

export const OperationalDecisionRecommendationsSection: React.FC<OperationalDecisionRecommendationsSectionProps> = ({ data }) => {
  if (!data || !data.summary) return null;

  const { summary, recommendations, insights } = data;

  const getPriorityBadge = (prio: string) => {
    switch (prio) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border inline-flex items-center gap-1 bg-rose-50 border-rose-200 text-rose-700">
            <AlertTriangle className="w-3 h-3" /> Urgent (P1)
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border inline-flex items-center gap-1 bg-amber-50 border-amber-200 text-amber-700">
            <Clock className="w-3 h-3" /> Priority (P2)
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border inline-flex items-center gap-1 bg-blue-50 border-blue-200 text-blue-700">
            <IconSupervisorDirectives className="w-3 h-3" /> Standard
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border inline-flex items-center gap-1 bg-slate-50 border-slate-200 text-slate-700">
            <CheckCircle2 className="w-3 h-3" /> Low
          </span>
        );
    }
  };

  return (
    <div className="space-y-5">
      {/* 1. Summary Ribbon: 5 Operational Opportunity KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard
          title="Active Directives"
          value={summary.active_recommendations}
          change={summary.active_recommendations > 0 ? 'Recommendations Available' : 'Nominal State'}
          changeType={summary.active_recommendations > 0 ? 'positive' : 'neutral'}
          subtitle="Real-time Dispatch Actions"
        />
        <KPICard
          title="High Priority Items"
          value={summary.high_priority_issues}
          change={summary.high_priority_issues > 0 ? 'Requires Dispatcher Action' : 'Zero High Risk'}
          changeType={summary.high_priority_issues > 0 ? 'negative' : 'positive'}
          subtitle="Immediate Bottlenecks"
        />
        <KPICard
          title="Potential Delay Reduction"
          value={`${summary.estimated_delay_reduction_mins}m`}
          change="Time Saved"
          changeType="positive"
          subtitle="Estimated Queue Savings"
        />
        <KPICard
          title="Est. SLA Recovery"
          value={`+${summary.estimated_sla_recovery_pct}%`}
          change="SLA Gain"
          changeType="positive"
          subtitle="Compliance Uplift"
        />
        <KPICard
          title="Fleet Efficiency Opportunity"
          value={`+${summary.fleet_efficiency_opportunity_pct}%`}
          change="Turnaround Gain"
          changeType="positive"
          subtitle="Throughput Optimization"
        />
      </div>

      {/* 2. Priority Dispatch Directives List */}
      <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
              <IconSupervisorDirectives className="w-4 h-4" /> Targeted Dispatch Optimization Directives
            </h3>
            <p className="text-[11px] font-medium text-slate-500">
              Specific operational actions derived from queue bottlenecks and turnaround patterns
            </p>
          </div>
          <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md border bg-blue-50 border-blue-200 text-blue-700">
            {recommendations.length} Active Directives
          </span>
        </div>

        <div className="space-y-3">
          {recommendations.length === 0 ? (
            <div className="text-xs italic py-6 text-center text-slate-400">Zero active operational recommendations</div>
          ) : (
            recommendations.map((rec) => (
              <div
                key={rec.recommendation_id}
                className="p-4 rounded-md border border-slate-200/80 bg-slate-50 space-y-3 transition hover:border-blue-400"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    {getPriorityBadge(rec.priority)}
                    <span className="font-bold text-sm text-slate-900">{rec.recommendation_text}</span>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="px-2 py-0.5 rounded-md border font-bold text-emerald-700 bg-emerald-50 border-emerald-200">
                      {rec.expected_impact}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {rec.confidence_pct}% Confidence
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200/80 text-xs font-mono text-slate-500">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span>Plant: <strong className="text-slate-900">{rec.affected_plant}</strong></span>
                    {rec.affected_vehicle && (
                      <>
                        <span>•</span>
                        <span>Vehicle: <strong className="text-blue-700">{rec.affected_vehicle}</strong></span>
                      </>
                    )}
                    <span>•</span>
                    <span className="italic text-slate-600">{rec.underlying_reason}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded-md border border-slate-200 bg-white font-bold text-slate-800">
                    Status: {rec.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 3. Operational Advisory & Throughput Guidelines */}
      <div className="border border-slate-200/90 rounded-lg p-5 space-y-4 bg-white shadow-xs">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
            <IconQualityAward className="w-4 h-4" /> Operational Advisory &amp; Best Practices
          </h3>
          <p className="text-[11px] font-medium mt-0.5 text-slate-500">
            Proactive operational adjustments to protect cycle times and maintain delivery SLAs
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {insights.map((card, idx) => (
            <div key={idx} className="p-4 rounded-md border border-slate-200/80 bg-slate-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900">{card.title}</span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border bg-blue-50 border-blue-200 text-blue-700">
                  {card.urgency}
                </span>
              </div>
              <p className="text-xs font-medium leading-relaxed text-slate-600">{card.description}</p>
              <div className="flex items-center justify-between text-[11px] font-mono pt-1 text-slate-500">
                <span>Area: <strong className="text-slate-900">{card.category}</strong></span>
                <span>Action: <strong className="text-blue-700">{card.action_type}</strong></span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
