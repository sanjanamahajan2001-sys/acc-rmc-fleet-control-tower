import React from 'react';
import { SummaryData } from './SiteSummaryPanel';

interface SiteSummaryCardProps {
  data: SummaryData | null;
  loading?: boolean;
}

export const SiteSummaryCard: React.FC<SiteSummaryCardProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="bg-white rounded-lg border border-slate-200/90 p-3 shadow-sm h-full animate-pulse space-y-2">
        <div className="h-3 w-28 bg-slate-200 rounded" />
        <div className="space-y-1.5 pt-1">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="h-2.5 bg-slate-100 rounded w-full" />
          ))}
        </div>
      </div>
    );
  }

  const formatQueueDuration = (mins: number) => {
    if (!mins) return '0 min';
    const hrs = Math.floor(mins / 60);
    const remainderMins = mins % 60;
    if (hrs > 0) {
      return `${hrs} hr ${remainderMins} min`;
    }
    return `${remainderMins} min`;
  };

  const metrics = [
    { label: 'Total Quantity', value: `${data.total_quantity_m3.toLocaleString()} Cum` },
    { label: 'Average Holding Time', value: `${data.avg_holding_mins} min` },
    { label: 'Average Retention Time', value: `${data.avg_retention_mins} min` },
    { label: 'Maximum Queue', value: `${data.max_queue_tms} TMs` },
    { label: 'Queue Duration', value: formatQueueDuration(data.queue_duration_mins) },
    { label: 'Total Overlap Minutes', value: `${data.total_overlap_mins} min` },
    { label: 'Weighted Overlap', value: `${data.weighted_overlap_tm_mins} TM-min` },
    { label: 'Dispatch Accuracy', value: `${data.dispatch_accuracy_pct}%`, isAccuracy: true },
  ];

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-3 shadow-2xs flex flex-col justify-between h-full min-w-0">
      <h3 className="text-[10.5px] font-bold tracking-tight uppercase border-b border-slate-100 pb-1.5 mb-1.5 text-slate-800">
        SITE SUMMARY <span className="font-normal text-slate-500">(YESTERDAY)</span>
      </h3>

      <div className="space-y-1 text-[11px] flex-1 flex flex-col justify-between">
        {metrics.map((m) => (
          <div key={m.label} className="flex justify-between items-center leading-tight">
            <span className="font-medium text-slate-500">{m.label}</span>
            <span className={`font-semibold font-mono tabular-nums ${m.isAccuracy ? 'text-emerald-700' : 'text-slate-900'}`}>
              {m.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
