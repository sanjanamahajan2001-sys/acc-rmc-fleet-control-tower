import React from 'react';
import {
  IconTransitMixer,
  IconHoldingHourglass,
  IconPlantRetentionFactory,
  IconCycleStopwatch,
  IconDispatchAccuracy,
} from '../../../../components/icons/LinealColorIcons';
import { SummaryData } from '../summary/SiteSummaryPanel';

export interface KPICardData {
  key: string;
  label: string;
  current_value: number;
  unit?: string;
  threshold?: number;
  target?: number;
  variance?: number;
  status: 'OPTIMAL' | 'WARNING' | 'CRITICAL';
  trend?: 'UP' | 'DOWN' | 'STABLE';
}

interface KPICardProps {
  data: KPICardData;
  summaryData?: SummaryData | null;
}

export const KPICard: React.FC<KPICardProps> = ({ data, summaryData }) => {
  const getCardTheme = () => {
    switch (data.key) {
      case 'dispatches':
        return {
          icon: <IconTransitMixer className="w-5 h-5" />,
          title: 'TOTAL DISPATCHES',
          valueColor: 'text-slate-900',
          secondary: (
            <div className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
              Total Quantity <span className="font-mono font-semibold text-slate-800">{summaryData?.total_quantity_m3 ? `${summaryData.total_quantity_m3.toLocaleString()} Cum` : '0 Cum'}</span>
            </div>
          ),
        };
      case 'holding':
        return {
          icon: <IconHoldingHourglass className="w-5 h-5" />,
          title: 'HOLDING BEYOND 20 MIN',
          valueColor: 'text-amber-800',
          secondary: (
            <div className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
              Avg Holding <span className="font-mono font-semibold text-slate-800">{summaryData?.avg_holding_mins ? `${summaryData.avg_holding_mins} min` : '0 min'}</span>
            </div>
          ),
        };
      case 'retention':
        return {
          icon: <IconPlantRetentionFactory className="w-5 h-5" />,
          title: 'RETENTION BEYOND 10 MIN',
          valueColor: 'text-rose-800',
          secondary: (
            <div className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
              Avg Retention <span className="font-mono font-semibold text-slate-800">{summaryData?.avg_retention_mins ? `${summaryData.avg_retention_mins} min` : '0 min'}</span>
            </div>
          ),
        };
      case 'unloading_60':
        return {
          icon: <IconCycleStopwatch className="w-5 h-5" />,
          title: 'UNLOADING BEYOND 60 MIN',
          valueColor: 'text-orange-800',
          secondary: (
            <div className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
              Threshold <span className="font-mono font-semibold text-slate-800">&gt; 60 min</span>
            </div>
          ),
        };
      case 'overlap':
        return {
          icon: <IconTransitMixer className="w-5 h-5" />,
          title: 'TM OVERLAP (WEIGHTED)',
          valueColor: 'text-slate-900',
          secondary: (
            <div className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
              Max Queue <span className="font-mono font-semibold text-slate-800">{summaryData?.max_queue_tms !== undefined ? `${summaryData.max_queue_tms} TMs` : '0 TMs'}</span>
            </div>
          ),
        };
      case 'accuracy':
        return {
          icon: <IconDispatchAccuracy className="w-5 h-5" />,
          title: 'DISPATCH ACCURACY',
          valueColor: 'text-emerald-800',
          secondary: (
            <div className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
              vs Target <span className="font-mono font-semibold text-slate-800">{data.target ?? 90}%</span>
            </div>
          ),
        };
      default:
        return {
          icon: <IconTransitMixer className="w-5 h-5" />,
          title: data.label.toUpperCase(),
          valueColor: 'text-slate-900',
          secondary: null,
        };
    }
  };

  const theme = getCardTheme();

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-3.5 shadow-2xs flex flex-col justify-between h-[112px] min-w-0 transition-all hover:border-slate-300">
      {/* Header: Icon + Uppercase Title */}
      <div className="flex items-center gap-2 min-w-0">
        <div className="shrink-0 flex items-center justify-center">
          {theme.icon}
        </div>
        <span className="text-[10.5px] font-bold tracking-tight truncate leading-tight uppercase text-slate-500">
          {theme.title}
        </span>
      </div>

      {/* Main KPI Value */}
      <div className="flex items-baseline gap-1.5 mt-1">
        <span className={`text-2xl font-black tracking-tight font-mono tabular-nums ${theme.valueColor}`}>
          {data.current_value.toLocaleString()}
        </span>
        {data.unit && (
          <span className="text-xs font-medium text-slate-500">
            {data.unit}
          </span>
        )}
      </div>

      {/* Secondary Line / Comparison text */}
      <div className="mt-auto pt-0.5">
        {theme.secondary}
      </div>
    </div>
  );
};

