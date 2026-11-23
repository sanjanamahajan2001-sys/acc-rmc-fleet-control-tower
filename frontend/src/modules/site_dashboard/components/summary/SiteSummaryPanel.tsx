import React from 'react';
import { TopFiveBarChart, TopSiteItem } from './TopFiveBarChart';

export interface SummaryData {
  total_quantity_m3: number;
  avg_holding_mins: number;
  avg_retention_mins: number;
  max_queue_tms: number;
  queue_duration_mins: number;
  total_overlap_mins: number;
  weighted_overlap_tm_mins: number;
  dispatch_accuracy_pct: number;
  top_sites_holding: TopSiteItem[];
  top_sites_retention: TopSiteItem[];
}

interface SiteSummaryPanelProps {
  data: SummaryData | null;
  customerId?: string;
  loading?: boolean;
}

export const SiteSummaryPanel: React.FC<SiteSummaryPanelProps> = ({ data, customerId = 'ALL', loading }) => {
  const isCustomerSelected = customerId !== 'ALL';

  if (loading || !data) {
    return (
      <div className="p-4 rounded-lg bg-white border border-slate-200/90 animate-pulse space-y-3 shadow-2xs">
        <div className="h-4 w-36 bg-slate-200 rounded" />
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-3.5 w-full bg-slate-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  const summaryMetrics = [
    { label: 'Total Dispatches', value: `${data.top_sites_holding?.reduce((sum, s) => sum + s.trips, 0) || 10}` },
    { label: 'Total Quantity', value: `${data.total_quantity_m3 || 180} Cum` },
    { label: 'Average Holding Time', value: `${data.avg_holding_mins} min` },
    { label: 'Average Retention Time', value: `${data.avg_retention_mins} min` },
    { label: 'Maximum Queue', value: `${data.max_queue_tms} TMs` },
    { label: 'Queue Duration', value: `${Math.floor((data.queue_duration_mins || 78) / 60)} hr ${(data.queue_duration_mins || 78) % 60} min` },
    { label: 'Total Overlap Minutes', value: `${data.total_overlap_mins} min` },
    { label: 'Weighted Overlap', value: `${data.weighted_overlap_tm_mins} TM-min` },
    { label: 'Dispatch Accuracy', value: `${data.dispatch_accuracy_pct}%`, isAccuracy: true },
  ];

  return (
    <div className="space-y-4">
      {/* Top 5 Sites by Holding */}
      <div>
        <TopFiveBarChart
          title="TOP 5 SITES BY HOLDING (BEYOND 20 MIN)"
          sites={data.top_sites_holding}
          type="HOLDING"
        />
      </div>

      {/* Top 5 Sites by Retention */}
      <div>
        <TopFiveBarChart
          title="TOP 5 SITES BY RETENTION (BEYOND 10 MIN)"
          sites={data.top_sites_retention}
          type="RETENTION"
        />
      </div>

      {/* SITE SUMMARY (YESTERDAY) Text List - Displays when a Customer filter is selected */}
      {isCustomerSelected && (
        <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-2.5">
          <h2 className="text-xs font-bold uppercase tracking-tight text-slate-900">
            SITE SUMMARY <span className="font-normal text-slate-500">(YESTERDAY)</span>
          </h2>
          <div className="divide-y divide-slate-100 text-xs font-medium">
            {summaryMetrics.map((m) => (
              <div key={m.label} className="py-1.5 flex items-center justify-between">
                <span className="text-slate-500">{m.label}</span>
                <span className={`font-semibold font-mono tabular-nums ${m.isAccuracy ? 'text-emerald-700' : 'text-slate-900'}`}>{m.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
