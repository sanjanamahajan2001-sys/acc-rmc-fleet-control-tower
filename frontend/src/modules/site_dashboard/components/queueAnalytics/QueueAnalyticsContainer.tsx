import React from 'react';
import { QueueTrendChart, QueuePoint } from './QueueTrendChart';
import { QueueStatisticsPanel, QueueData } from './QueueStatisticsPanel';
import { CauseItem } from './QueueReasonTable';

export interface QueueAnalyticsContainerData {
  queue: QueueData & { points: QueuePoint[] };
  root_causes: CauseItem[];
}

interface QueueAnalyticsContainerProps {
  data: QueueAnalyticsContainerData | null;
  timelineData?: any;
  loading?: boolean;
}

export const QueueAnalyticsContainer: React.FC<QueueAnalyticsContainerProps> = ({ data, timelineData, loading }) => {
  if (loading || !data) {
    return (
      <div className="bg-white rounded-lg border border-slate-200/90 p-4 shadow-sm animate-pulse space-y-3">
        <div className="h-4 w-48 bg-slate-200 rounded" />
        <div className="h-44 w-full bg-slate-100 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3">
      {/* Widget Header */}
      <h2 className="text-xs font-bold uppercase tracking-tight text-slate-800">
        QUEUE AT SITE OVER TIME <span className="font-normal text-slate-500">(NUMBER OF TMS)</span>
      </h2>

      {/* Stacked Layout: Full-Width Chart on Top, Horizontal Metrics Below for Maximum Chart Visibility */}
      <div className="flex flex-col space-y-4 pt-1">
        {/* Top: Full-Width Queue Trend SVG Line Chart */}
        <div className="w-full">
          <QueueTrendChart points={data.queue.points || []} timelineData={timelineData} />
        </div>

        {/* Bottom: Horizontal Statistics Panel with Icons */}
        <div className="pt-2 border-t border-slate-100">
          <QueueStatisticsPanel data={data.queue} />
        </div>
      </div>
    </div>
  );
};

