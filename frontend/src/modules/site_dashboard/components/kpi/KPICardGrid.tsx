import React from 'react';
import { KPICard, KPICardData } from './KPICard';
import { SiteSummaryCard } from '../summary/SiteSummaryCard';
import { SummaryData } from '../summary/SiteSummaryPanel';

interface KPICardGridProps {
  cards: KPICardData[];
  summaryData?: SummaryData | null;
  customerId?: string;
  loading?: boolean;
}

export const KPICardGrid: React.FC<KPICardGridProps> = ({ cards, summaryData, customerId = 'ALL', loading }) => {
  const isCustomerSelected = customerId !== 'ALL';

  if (loading) {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 ${isCustomerSelected ? 'lg:grid-cols-5' : 'lg:grid-cols-6'} gap-3`}>
        {[1, 2, 3, 4, 5, isCustomerSelected ? null : 6].filter(Boolean).map((i) => (
          <div key={i} className="h-[112px] rounded-lg bg-white border border-slate-200 animate-pulse p-3 space-y-2">
            <div className="h-3 w-24 bg-slate-200 rounded" />
            <div className="h-6 w-16 bg-slate-200 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 ${isCustomerSelected ? 'lg:grid-cols-5' : 'lg:grid-cols-6'} gap-3 items-stretch`}>
      {cards.map((card) => (
        <KPICard key={card.key} data={card} summaryData={summaryData} />
      ))}
      {!isCustomerSelected && <SiteSummaryCard data={summaryData || null} loading={loading} />}
    </div>
  );
};

