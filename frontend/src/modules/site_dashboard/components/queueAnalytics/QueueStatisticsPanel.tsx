import React from 'react';
import {
  IconHoldingQueueHourglass,
  IconCriticalAlert,
  IconCycleStopwatch,
  IconSyncRefresh,
  IconAnalyticsBarChart,
} from '../../../../components/icons/LinealColorIcons';

export interface QueueData {
  avg_queue: number;
  max_queue: number;
  queue_duration_hours: number;
  total_overlap_mins: number;
  weighted_overlap_tm_mins: number;
}

interface QueueStatisticsPanelProps {
  data: QueueData;
}

export const QueueStatisticsPanel: React.FC<QueueStatisticsPanelProps> = ({ data }) => {
  const formatDuration = (hrs: number) => {
    if (!hrs) return '0 min';
    const totalMins = Math.round(hrs * 60);
    const h = Math.floor(totalMins / 60);
    const m = totalMins % 60;
    if (h > 0) return `${h} hr ${m} min`;
    return `${m} min`;
  };

  const stats = [
    {
      label: 'Average Queue',
      value: `${data.avg_queue} TMs`,
      icon: <IconHoldingQueueHourglass className="w-5 h-5" />,
    },
    {
      label: 'Maximum Queue',
      value: `${data.max_queue} TMs`,
      icon: <IconCriticalAlert className="w-5 h-5" />,
    },
    {
      label: 'Queue Duration',
      value: formatDuration(data.queue_duration_hours),
      icon: <IconCycleStopwatch className="w-5 h-5" />,
    },
    {
      label: 'Total Overlap Minutes',
      value: `${data.total_overlap_mins} min`,
      icon: <IconSyncRefresh className="w-5 h-5" />,
    },
    {
      label: 'Weighted Overlap',
      value: `${data.weighted_overlap_tm_mins} TM-min`,
      icon: <IconAnalyticsBarChart className="w-5 h-5" />,
    },
  ];

  const row1Stats = stats.slice(0, 3);
  const row2Stats = stats.slice(3, 5);

  return (
    <div className="w-full space-y-2 pt-1">
      {/* Row 1: First 3 Metrics */}
      <div className="grid grid-cols-3 gap-2.5">
        {row1Stats.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5 p-2 rounded-lg bg-slate-50/80 border border-slate-200/70">
            <div className="shrink-0 flex items-center justify-center">
              {item.icon}
            </div>
            <div className="min-w-0">
              <p className="text-[10px] text-slate-500 font-medium uppercase truncate">{item.label}</p>
              <p className="text-xs font-bold text-slate-900 font-mono tabular-nums truncate">{item.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Row 2: Next 2 Metrics (Total Overlap & Weighted Overlap) */}
      <div className="grid grid-cols-2 gap-2.5">
        {row2Stats.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5 p-2 rounded-lg bg-slate-50/80 border border-slate-200/70">
            <div className="shrink-0 flex items-center justify-center">
              {item.icon}
            </div>
            <div className="min-w-0">
              <p className="text-[10px] text-slate-500 font-medium uppercase truncate">{item.label}</p>
              <p className="text-xs font-bold text-slate-900 font-mono tabular-nums truncate">{item.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

