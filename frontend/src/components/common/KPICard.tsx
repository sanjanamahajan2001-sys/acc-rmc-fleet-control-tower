import React from 'react';

export interface KPICardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ReactNode;
  subtitle?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  change,
  changeType = 'neutral',
  icon,
  subtitle,
}) => {
  return (
    <div className="p-4 rounded-lg border border-slate-200/90 shadow-xs transition space-y-2.5 hover:border-slate-300 bg-white h-full flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            {title}
          </span>
          {icon && (
            <div className="p-1.5 rounded-md border bg-blue-50 text-blue-700 border-blue-200">
              {icon}
            </div>
          )}
        </div>

        <div className="flex items-baseline justify-between gap-2 mt-2">
          <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">
            {value}
          </span>
          {change && (
            <span
              className={`text-[11px] font-bold px-2 py-0.5 rounded-md border shrink-0 ${
                changeType === 'positive'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                  : changeType === 'negative'
                  ? 'bg-rose-50 border-rose-200 text-rose-700'
                  : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}
            >
              {change}
            </span>
          )}
        </div>
      </div>

      {subtitle && (
        <p className="text-[11px] font-medium text-slate-500 pt-1 border-t border-slate-100">{subtitle}</p>
      )}
    </div>
  );
};
