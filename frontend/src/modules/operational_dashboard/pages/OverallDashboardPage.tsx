import React, { useState } from 'react';
import { OperationalDashboardShell } from '../shell/OperationalDashboardShell';
import { OperationalIntelligenceGrid } from '../components/OperationalIntelligenceGrid';
import { DASDetailModal } from '../components/DASDetailModal';
import { useDASOverview } from '../hooks/useDASOverview';
import { useDASDetails } from '../hooks/useDASDetails';

const OverallDashboardContent: React.FC = () => {
  const [isDASModalOpen, setIsDASModalOpen] = useState<boolean>(false);
  const { data: overviewData } = useDASOverview();
  const { data: detailsData, isLoading: isDetailsLoading } = useDASDetails();

  return (
    <>
      <OperationalIntelligenceGrid onOpenDASDetailModal={() => setIsDASModalOpen(true)} />
      <DASDetailModal
        isOpen={isDASModalOpen}
        onClose={() => setIsDASModalOpen(false)}
        summary={detailsData?.summary || overviewData?.summary}
        buckets={detailsData?.buckets || overviewData?.buckets}
        detailRows={detailsData?.data || []}
        hasDetailApi={true}
        isLoading={isDetailsLoading}
      />
    </>
  );
};

export const OverallDashboardPage: React.FC = () => {
  return (
    <OperationalDashboardShell>
      <OverallDashboardContent />
    </OperationalDashboardShell>
  );
};

export default OverallDashboardPage;
