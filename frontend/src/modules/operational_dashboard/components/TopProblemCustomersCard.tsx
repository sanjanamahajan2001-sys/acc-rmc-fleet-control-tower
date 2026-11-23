import React, { useState } from 'react';
import { useTopProblemCustomers, OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { TopProblemCustomersDrawer } from './TopProblemCustomersDrawer';
import { IconCriticalAlert } from '../../../components/icons/LinealColorIcons';

export const TopProblemCustomersCard: React.FC = () => {
  const { data, loading, error } = useTopProblemCustomers();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const customers = data?.data || [];
  const top10 = customers.slice(0, 10);
  const totalCount = data?.total_count || customers.length;
  const isNoObs = data?.status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || customers.length === 0;

  return (
    <>
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <IconCriticalAlert className="w-4 h-4" />
                TOP 10 PROBLEM CUSTOMERS
              </h3>
              <p className="text-[11px] font-normal text-slate-500 mt-0.5">By Total Lost Hours (Holding &gt; 20m + Retention &gt; 10m)</p>
            </div>
          </div>

          {/* Body Content */}
          <div className="mt-3 min-h-[220px]">
            {loading ? (
              <div className="space-y-2 animate-pulse py-2">
                <div className="h-4 rounded bg-slate-100 w-full" />
                <div className="h-7 rounded bg-slate-100 w-full" />
                <div className="h-7 rounded bg-slate-100 w-full" />
                <div className="h-7 rounded bg-slate-100 w-full" />
              </div>
            ) : error ? (
              <div className="py-6 text-center text-xs rounded-md border border-rose-200 bg-rose-50 p-3 font-semibold text-rose-700">
                {error}
              </div>
            ) : isNoObs ? (
              <div className="py-10 text-center text-xs rounded-md border border-slate-200 bg-slate-50 p-4 text-slate-500">
                No customer observations available for this scope.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider font-semibold border-b border-slate-200 text-slate-500 bg-slate-50">
                    <tr>
                      <th scope="col" className="py-2 px-2">Customer</th>
                      <th scope="col" className="py-2 px-1 text-right">Holding (h)</th>
                      <th scope="col" className="py-2 px-1 text-right">Retention (h)</th>
                      <th scope="col" className="py-2 px-1 text-right">Total Lost (h)</th>
                      <th scope="col" className="py-2 px-2 text-right">CEI</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {top10.map((c) => (
                      <tr key={c.customer_id} className="hover:bg-slate-50/75 transition-colors">
                        <td className="py-2 px-2 font-medium text-slate-900 truncate max-w-[130px]" title={c.customer_name}>
                          {c.customer_name}
                        </td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums text-slate-600">
                          {c.holding_hours.toFixed(1)}
                        </td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums text-slate-600">
                          {c.retention_hours.toFixed(1)}
                        </td>
                        <td className="py-2 px-1 text-right font-mono tabular-nums font-bold text-rose-700">
                          {c.total_lost_hours.toFixed(1)}
                        </td>
                        <td className="py-2 px-2 text-right font-mono tabular-nums font-semibold text-slate-800">
                          {c.cei !== null && c.cei !== undefined ? c.cei.toFixed(1) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Footer Trigger for Drawer */}
        <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-[11px] font-normal text-slate-500">
            Top 10 of {totalCount} Problem Customers
          </span>
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors flex items-center gap-1"
          >
            View All Customers &rarr;
          </button>
        </div>
      </div>

      {/* Detail Drawer Overlay */}
      <TopProblemCustomersDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        customers={customers}
        totalCount={totalCount}
      />
    </>
  );
};

