import React, { useState } from 'react';
import { useCustomerEfficiency } from '../hooks/useCustomerEfficiency';
import { useTopProblemCustomers } from '../hooks/useTopProblemCustomers';
import { TopProblemCustomersDrawer } from './TopProblemCustomersDrawer';
import { IconQualityAward } from '../../../components/icons/LinealColorIcons';

export const CustomerEfficiencyIndexCard: React.FC = () => {
  const { data, loading, error } = useCustomerEfficiency();
  const { data: problemData } = useTopProblemCustomers();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const allCustomers = data?.data || [];

  // Filter & prioritize customers that genuinely have CEI data
  const dataBearingCustomers = allCustomers.filter(
    (c) => c.cei_score !== null && c.cei_score !== undefined && c.cei_score > 0
  );

  // Take top 5 data-bearing customers, fallback to first 5 if none available
  const top5Preview = dataBearingCustomers.length > 0
    ? dataBearingCustomers.slice(0, 5)
    : allCustomers.slice(0, 5);

  const allProblemCustomers = problemData?.data || [];
  const totalCount = problemData?.total_count || allProblemCustomers.length;

  const isEvaluated = (score: number) => {
    return score !== null && score !== undefined && score > 0;
  };

  const getGradeBadge = (score: number, grade: string) => {
    if (!isEvaluated(score)) {
      return (
        <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-slate-400 bg-slate-100 border border-slate-200">
          Not Rated
        </span>
      );
    }

    switch (grade?.toLowerCase()) {
      case 'excellent':
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200">Optimal</span>;
      case 'good':
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200">Good</span>;
      case 'average':
      case 'needs improvement':
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200">Average</span>;
      case 'critical':
      case 'poor':
      default:
        return <span className="px-1.5 py-0.5 rounded-md text-[11px] font-medium text-rose-700 bg-rose-50 border border-rose-200">Poor</span>;
    }
  };

  const renderTrendSparkline = (trend: string, score: number) => {
    if (!isEvaluated(score) || !trend) {
      return <span className="text-slate-400 font-medium">—</span>;
    }

    const isUp = trend === 'UP';
    const isDown = trend === 'DOWN';

    return (
      <div className="inline-flex items-center gap-1.5 justify-end">
        <div className="inline-flex items-end gap-0.5 h-3.5 px-0.5">
          <span className={`w-1 rounded-t ${isUp ? 'bg-emerald-400 h-1.5' : isDown ? 'bg-rose-500 h-3' : 'bg-slate-300 h-2'}`} />
          <span className={`w-1 rounded-t ${isUp ? 'bg-emerald-500 h-2' : isDown ? 'bg-rose-400 h-2.5' : 'bg-slate-300 h-2'}`} />
          <span className={`w-1 rounded-t ${isUp ? 'bg-emerald-500 h-2.5' : isDown ? 'bg-rose-400 h-2' : 'bg-slate-300 h-2'}`} />
          <span className={`w-1 rounded-t ${isUp ? 'bg-emerald-600 h-3.5' : isDown ? 'bg-rose-300 h-1.5' : 'bg-slate-300 h-2'}`} />
        </div>
        <span className={`text-[11px] font-medium ${isUp ? 'text-emerald-700' : isDown ? 'text-rose-700' : 'text-slate-500'}`}>
          {isUp ? '▲ Up' : isDown ? '▼ Down' : '• Flat'}
        </span>
      </div>
    );
  };

  return (
    <>
      <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <IconQualityAward className="w-4 h-4" />
                CUSTOMER EFFICIENCY INDEX (CEI)
              </h3>
              <p className="text-[11px] font-normal text-slate-500 mt-0.5">Commercial Account Performance &amp; Retention Score</p>
            </div>
          </div>

          {/* Content Body */}
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
            ) : top5Preview.length === 0 ? (
              <div className="py-10 text-center text-xs rounded-md p-4 border border-slate-200 bg-slate-50 text-slate-500">
                No customer efficiency data available for this scope.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider font-semibold border-b border-slate-200 text-slate-500 bg-slate-50">
                    <tr>
                      <th scope="col" className="py-2 px-2">Customer</th>
                      <th scope="col" className="py-2 px-1 text-center">Score</th>
                      <th scope="col" className="py-2 px-1 text-center">Grade</th>
                      <th scope="col" className="py-2 px-2 text-right">Trend</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {top5Preview.map((c, idx) => {
                      const evaluated = isEvaluated(c.cei_score);

                      return (
                        <tr key={c.customer_id || idx} className="hover:bg-slate-50/75 transition-colors">
                          <td className="py-2 px-2 font-medium text-slate-900 truncate max-w-[130px]" title={c.customer_name}>
                            {c.customer_name}
                          </td>
                          <td className="py-2 px-1 text-center font-mono tabular-nums font-bold text-slate-900">
                            {evaluated ? Math.round(c.cei_score) : '—'}
                          </td>
                          <td className="py-2 px-1 text-center">
                            {getGradeBadge(c.cei_score, c.grade)}
                          </td>
                          <td className="py-2 px-2 text-right">
                            {renderTrendSparkline(c.trend, c.cei_score)}
                          </td>
                        </tr>
                      );
                    })}
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
            onClick={() => setIsDrawerOpen(true)}
            disabled={loading || !!error}
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            View all customers &rarr;
          </button>
        </div>
      </div>

      {/* Side Drawer Overlay for All Customers */}
      <TopProblemCustomersDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        customers={allProblemCustomers}
        totalCount={totalCount}
      />
    </>
  );
};

