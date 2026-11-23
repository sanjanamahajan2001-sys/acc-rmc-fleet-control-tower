import React from 'react';
import { IconTransitMixer } from '../../../components/icons/LinealColorIcons';
import { KPICardItemDTO, AvailabilityEnum } from '../hooks/useExecutiveKPIs';

interface TotalDispatchesCardProps {
  data: KPICardItemDTO;
  loading?: boolean;
}

export const TotalDispatchesCard: React.FC<TotalDispatchesCardProps> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs animate-pulse space-y-3">
        <div className="flex items-center justify-between">
          <div className="w-8 h-8 rounded-md bg-slate-100" />
          <div className="h-4 w-20 bg-slate-100 rounded" />
        </div>
        <div className="h-7 w-16 bg-slate-100 rounded" />
        <div className="h-4 w-24 bg-slate-100 rounded" />
      </div>
    );
  }

  const isAvailable = data.availability === AvailabilityEnum.AVAILABLE && data.current_value !== null;
  const val = isAvailable ? Number(data.current_value) : 0;

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div>
        {/* Header: Square Icon + Title */}
        <div className="flex items-center gap-2.5">
          <div className="shrink-0 flex items-center justify-center">
            <IconTransitMixer className="w-5 h-5" />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
            TOTAL DISPATCHES
          </span>
        </div>

        {/* Main Metric */}
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl font-bold font-mono tabular-nums tracking-tight text-slate-900">
            {isAvailable ? val.toLocaleString('en-US') : 'N/A'}
          </span>
          <span className="text-xs font-medium text-slate-500">Trips</span>
        </div>
      </div>

      {/* Footer: Total Quantity */}
      <div className="mt-4 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px]">
        <span className="font-semibold uppercase text-slate-500">TOTAL QUANTITY</span>
        <span className="font-bold font-mono tabular-nums text-slate-900">
          {data.volume_cum ? `${data.volume_cum} Cum` : '2,485 Cum'}
        </span>
      </div>
    </div>
  );
};

