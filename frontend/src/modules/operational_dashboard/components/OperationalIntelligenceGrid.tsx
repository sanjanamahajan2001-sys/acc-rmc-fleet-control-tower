import React from 'react';
import { TopProblemCustomersCard } from './TopProblemCustomersCard';
import { OverlapHeatMapCard } from './OverlapHeatMapCard';
import { SiteReadinessCard } from './SiteReadinessCard';
import { HoldingRetentionCard } from './HoldingRetentionCard';
import { DASOverviewCard } from './DASOverviewCard';
import { PotentialImpactPlanningCard } from './PotentialImpactPlanningCard';
import { CustomerEfficiencyIndexCard } from './CustomerEfficiencyIndexCard';
import { RecentAlertsCard } from './RecentAlertsCard';
import { TodaysSummaryCard } from './TodaysSummaryCard';

interface OperationalIntelligenceGridProps {
  onOpenDASDetailModal?: () => void;
}

export const OperationalIntelligenceGrid: React.FC<OperationalIntelligenceGridProps> = ({
  onOpenDASDetailModal,
}) => {
  return (
    <div className="space-y-5">
      {/* Row 2: Executive Intelligence (Top 10 Problem Customers, Overlap Heat Map, Site Readiness Index) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <TopProblemCustomersCard />
        <OverlapHeatMapCard />
        <SiteReadinessCard />
      </div>

      {/* Row 3: Operational Intelligence (Holding & Retention, DAS Donut, Potential Impact of Better Planning) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <HoldingRetentionCard />
        <DASOverviewCard onOpenDetailModal={onOpenDASDetailModal} />
        <PotentialImpactPlanningCard />
      </div>

      {/* Row 4: Lower Operational Intelligence (Recent Alerts, Customer Efficiency Index, Today's Summary) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <RecentAlertsCard />
        <CustomerEfficiencyIndexCard />
        <TodaysSummaryCard />
      </div>
    </div>
  );
};
