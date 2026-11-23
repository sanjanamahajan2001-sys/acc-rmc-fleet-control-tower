import React from 'react';

export interface TMDetailItem {
  dispatch_id: string;
  tm_no: string;
  vehicle_plate: string;
  plant_name: string;
  customer_name: string;
  dispatch_time: string;
  site_in_time: string;
  unload_start_time: string;
  unload_end_time: string;
  site_out_time: string;
  holding_mins: number;
  unloading_mins: number;
  retention_mins: number;
  total_site_mins: number;
  dispatch_accuracy_pct: number;
  operational_status: string;
  sla_status: string;
  delay_classification: string;
}

interface TMDetailsRowProps {
  item: TMDetailItem;
  isDark?: boolean;
}

export const TMDetailsRow: React.FC<TMDetailsRowProps> = ({ item, isDark }) => {
  // Threshold helper: Holding (Grace = 20 min), Retention (Grace = 10 min)
  const getHoldingColorClass = (mins: number, dark: boolean) => {
    if (mins <= 20) return dark ? 'text-emerald-400 font-bold' : 'text-emerald-600 font-bold';
    if (mins <= 35) return dark ? 'text-amber-400 font-bold' : 'text-amber-600 font-bold';
    return dark ? 'text-rose-400 font-extrabold' : 'text-rose-600 font-extrabold';
  };

  const getRetentionColorClass = (mins: number, dark: boolean) => {
    if (mins <= 10) return dark ? 'text-emerald-400 font-bold' : 'text-emerald-600 font-bold';
    if (mins <= 20) return dark ? 'text-amber-400 font-bold' : 'text-amber-600 font-bold';
    return dark ? 'text-rose-400 font-extrabold' : 'text-rose-600 font-extrabold';
  };

  if (isDark) {
    return (
      <tr className="hover:bg-slate-800/60 transition border-b border-slate-800/60 text-xs">
        <td className="px-3 py-2.5 font-bold text-slate-200 font-mono">{item.tm_no}</td>
        <td className="px-3 py-2.5 text-center text-slate-300 font-mono">{item.site_in_time}</td>
        <td className="px-3 py-2.5 text-center text-slate-300 font-mono">{item.unload_start_time}</td>
        <td className="px-3 py-2.5 text-center text-slate-300 font-mono">{item.unload_end_time}</td>
        <td className="px-3 py-2.5 text-center text-slate-300 font-mono">{item.site_out_time}</td>
        <td className={`px-3 py-2.5 text-center font-mono ${getHoldingColorClass(item.holding_mins, true)}`}>
          {item.holding_mins} min
        </td>
        <td className={`px-3 py-2.5 text-center font-mono ${getRetentionColorClass(item.retention_mins, true)}`}>
          {item.retention_mins} min
        </td>
      </tr>
    );
  }

  return (
    <tr className="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
      <td className="px-3 py-2 font-bold font-mono text-slate-900">{item.tm_no}</td>
      <td className="px-3 py-2 text-center text-slate-700 font-mono tabular-nums">{item.site_in_time}</td>
      <td className="px-3 py-2 text-center text-slate-700 font-mono tabular-nums">{item.unload_start_time}</td>
      <td className="px-3 py-2 text-center text-slate-700 font-mono tabular-nums">{item.unload_end_time}</td>
      <td className="px-3 py-2 text-center text-slate-700 font-mono tabular-nums">{item.site_out_time}</td>
      <td className={`px-3 py-2 text-center font-mono tabular-nums ${getHoldingColorClass(item.holding_mins, false)}`}>
        {item.holding_mins} min
      </td>
      <td className={`px-3 py-2 text-center font-mono tabular-nums ${getRetentionColorClass(item.retention_mins, false)}`}>
        {item.retention_mins} min
      </td>
    </tr>
  );
};

