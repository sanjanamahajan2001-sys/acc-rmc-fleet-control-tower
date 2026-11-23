import React from 'react';
import { useRecentAlerts } from '../hooks/useRecentAlerts';
import { useNavigate } from 'react-router-dom';
import { IconIncidentSiren } from '../../../components/icons/LinealColorIcons';

export const RecentAlertsCard: React.FC = () => {
  const { alerts, loading, error } = useRecentAlerts();
  const navigate = useNavigate();

  const top5Alerts = alerts.slice(0, 5);

  const getImpactBadge = (impact: string) => {
    switch (impact?.toUpperCase()) {
      case 'HIGH':
      case 'CRITICAL':
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-rose-700 bg-rose-50 border border-rose-200">High</span>;
      case 'MEDIUM':
      case 'WARNING':
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200">Medium</span>;
      case 'LOW':
      default:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200">Low</span>;
    }
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <IconIncidentSiren className="w-4 h-4" />
              RECENT ALERTS
            </h3>
            <p className="text-[11px] font-normal text-slate-500 mt-0.5">Live Operational Exceptions &amp; Turnaround Bottlenecks</p>
          </div>
        </div>

        {/* Content Body: Alerts Table */}
        <div className="mt-3 min-h-[200px]">
          {loading ? (
            <div className="space-y-2 animate-pulse py-2">
              <div className="h-4 rounded bg-slate-100 w-full" />
              <div className="h-7 rounded bg-slate-100 w-full" />
              <div className="h-7 rounded bg-slate-100 w-full" />
            </div>
          ) : error ? (
            <div className="py-6 text-center text-xs rounded-md p-3 font-semibold border border-rose-200 bg-rose-50 text-rose-700">
              {error}
            </div>
          ) : alerts.length === 0 ? (
            <div className="py-10 text-center text-xs rounded-md p-4 border border-slate-200 bg-slate-50 text-slate-500">
              No recent active alerts detected.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs table-fixed">
                <thead className="text-[10px] uppercase tracking-wider font-semibold border-b border-slate-200 text-slate-500 bg-slate-50">
                  <tr>
                    <th scope="col" className="py-2 px-1 font-semibold w-[60px]">Time</th>
                    <th scope="col" className="py-2 px-1 font-semibold w-[100px]">Type</th>
                    <th scope="col" className="py-2 px-1 font-semibold w-[120px]">Site/Cust</th>
                    <th scope="col" className="py-2 px-1 font-semibold w-[75px]">Vehicle</th>
                    <th scope="col" className="py-2 px-1 font-semibold">Alert</th>
                    <th scope="col" className="py-2 px-1 text-right font-semibold w-[55px]">Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {top5Alerts.map((a, idx) => (
                    <tr key={a.id || idx} className="hover:bg-slate-50/75 transition-colors">
                      <td className="py-2 px-1 font-mono text-[11px] text-slate-500 whitespace-nowrap">{a.time || '08:10 AM'}</td>
                      <td className="py-2 px-1 font-medium text-[11px] text-slate-700 truncate" title={a.type || 'Retention'}>
                        {a.type || 'Retention'}
                      </td>
                      <td className="py-2 px-1 font-medium text-[11px] text-slate-900 truncate" title={a.site_or_customer || 'ABC Builders'}>
                        {a.site_or_customer || 'ABC Builders'}
                      </td>
                      <td className="py-2 px-1 font-mono text-[11px] text-slate-600 truncate" title={a.vehicle || 'GA03T1234'}>
                        {a.vehicle || 'GA03T1234'}
                      </td>
                      <td className="py-2 px-1 text-[11px] text-slate-600 truncate" title={a.alert_message}>
                        {a.alert_message || 'Vehicle retained after unloading'}
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        {getImpactBadge(a.impact)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Footer Action Link */}
      <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs">
        <button
          type="button"
          onClick={() => navigate('/alerts')}
          className="text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors flex items-center gap-1"
        >
          View all alerts &rarr;
        </button>
      </div>
    </div>
  );
};

