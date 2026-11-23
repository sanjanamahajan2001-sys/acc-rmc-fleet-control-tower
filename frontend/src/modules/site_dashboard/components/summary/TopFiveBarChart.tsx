import React from 'react';

export interface TopSiteItem {
  site_code: string;
  site_name: string;
  value: number;
  unit: string;
  avg_mins?: number;
  trips?: number;
}

interface TopFiveBarChartProps {
  title: string;
  sites: TopSiteItem[];
  type: 'HOLDING' | 'RETENTION';
}

export const TopFiveBarChart: React.FC<TopFiveBarChartProps> = ({ title, sites, type }) => {
  const maxValue = Math.max(...sites.map((s) => s.value), 1.0);

  const barColor = type === 'HOLDING' ? 'bg-amber-600' : 'bg-orange-600';

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3">
      {/* Title */}
      <h3 className="text-xs font-bold uppercase tracking-tight text-slate-800">
        {title}
      </h3>

      {sites.length === 0 ? (
        <p className="text-xs italic py-2 text-slate-400">No site data available</p>
      ) : (
        <div className="space-y-1.5">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-2 text-[10px] font-bold uppercase border-b border-slate-100 pb-1.5 px-1 text-slate-500">
            <div className="col-span-4">Site</div>
            <div className="col-span-4 text-center">
              {type === 'HOLDING' ? 'Total Holding' : 'Total Retention'}
            </div>
            <div className="col-span-2 text-right">
              {type === 'HOLDING' ? 'Avg Holding' : 'Avg Retention'}
            </div>
            <div className="col-span-2 text-right">Trips</div>
          </div>

          {/* Table Rows */}
          {sites.map((site) => {
            const pct = Math.min(100, (site.value / maxValue) * 100);
            const avgTime = site.avg_mins !== undefined ? `${site.avg_mins} min` : `${Math.round(site.value * 5)} min`;
            const tripCount = site.trips !== undefined ? site.trips : Math.round(site.value * 3);

            return (
              <div
                key={site.site_code}
                className="grid grid-cols-12 gap-2 items-center text-xs py-1 px-1 rounded transition hover:bg-slate-50"
              >
                {/* Site Name */}
                <div className="col-span-4 font-medium truncate text-[11px] text-slate-800" title={site.site_name}>
                  {site.site_name}
                </div>

                {/* Bar + Value */}
                <div className="col-span-4 flex items-center gap-2">
                  <div className="h-2 flex-1 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${barColor}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-semibold font-mono tabular-nums text-slate-700 w-12 text-right shrink-0">
                    {site.value} {site.unit}
                  </span>
                </div>

                {/* Avg Time */}
                <div className="col-span-2 text-right text-[11px] text-slate-600 font-medium font-mono tabular-nums">
                  {avgTime}
                </div>

                {/* Trips Count */}
                <div className="col-span-2 text-right text-[11px] font-bold font-mono tabular-nums text-slate-900">
                  {tripCount}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

