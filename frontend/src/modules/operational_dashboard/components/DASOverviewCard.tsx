import React from 'react';
import ReactECharts from 'echarts-for-react';
import { useDASOverview } from '../hooks/useDASOverview';
import { IconDispatchAccuracy } from '../../../components/icons/LinealColorIcons';

interface DASOverviewCardProps {
  onOpenDetailModal?: () => void;
}

export const DASOverviewCard: React.FC<DASOverviewCardProps> = ({ onOpenDetailModal }) => {
  const { data, loading, error } = useDASOverview();

  const summary = data?.summary;
  const buckets = data?.buckets;

  const dasScore = summary?.das_score !== null && summary?.das_score !== undefined ? Math.round(summary.das_score) : 0;
  const within20mCount = buckets?.within_20m_count ?? 0;
  const within20mPct = buckets?.within_20m_pct ?? 0;
  
  const range21_40mCount = buckets?.range_21_40m_count ?? buckets?.moderate_20_40m_count ?? 0;
  const range21_40mPct = buckets?.range_21_40m_pct ?? buckets?.moderate_20_40m_pct ?? 0;

  const range41_60mCount = buckets?.range_41_60m_count ?? 0;
  const range41_60mPct = buckets?.range_41_60m_pct ?? 0;

  const above60mCount = buckets?.above_60m_count ?? (buckets?.critical_above_40m_count ? Math.max(0, buckets.critical_above_40m_count - range41_60mCount) : 0);
  const above60mPct = buckets?.above_60m_pct ?? 0;

  const getDonutOption = () => {
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        textStyle: { color: '#0f172a', fontSize: 11 },
      },
      series: [
        {
          name: 'Dispatch Accuracy',
          type: 'pie',
          radius: ['65%', '85%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 3, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data: [
            { value: within20mCount, name: 'Within 20 min', itemStyle: { color: '#16a34a' } },
            { value: range21_40mCount, name: '21 - 40 min', itemStyle: { color: '#d97706' } },
            { value: range41_60mCount, name: '41 - 60 min', itemStyle: { color: '#ea580c' } },
            { value: above60mCount, name: 'After 60 min', itemStyle: { color: '#dc2626' } },
          ],
        },
      ],
    };
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-colors">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <IconDispatchAccuracy className="w-4 h-4" />
              DISPATCH ACCURACY (DAS)
            </h3>
            <p className="text-[11px] font-normal text-slate-500 mt-0.5">Holding Compliance &amp; Delay Bucket Distribution</p>
          </div>
        </div>

        {/* Content Body: Donut + Legend */}
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 items-center min-h-[190px]">
          {/* Donut Chart with Centered Score */}
          <div className="relative flex justify-center items-center h-44">
            {loading ? (
              <div className="w-32 h-32 rounded-full border-4 border-slate-100 animate-pulse" />
            ) : (
              <>
                <ReactECharts option={getDonutOption()} style={{ height: '170px', width: '170px' }} />
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-2xl font-bold font-mono tabular-nums text-slate-900">{dasScore}%</span>
                  <span className="text-[10px] font-medium text-slate-500">Dispatch Accuracy</span>
                </div>
              </>
            )}
          </div>

          {/* Side Legend Breakdown */}
          <div className="space-y-2.5 text-xs">
            <div className="flex items-start gap-2">
              <span className="w-2.5 h-2.5 rounded-sm mt-0.5 shrink-0 bg-emerald-600" />
              <div>
                <p className="font-medium text-slate-900 leading-tight">Within 20 min</p>
                <p className="font-mono tabular-nums text-[11px] text-slate-500">{within20mCount} ({within20mPct}%)</p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="w-2.5 h-2.5 rounded-sm mt-0.5 shrink-0 bg-amber-600" />
              <div>
                <p className="font-medium text-slate-900 leading-tight">21 – 40 min</p>
                <p className="font-mono tabular-nums text-[11px] text-slate-500">{range21_40mCount} ({range21_40mPct}%)</p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="w-2.5 h-2.5 rounded-sm mt-0.5 shrink-0 bg-orange-600" />
              <div>
                <p className="font-medium text-slate-900 leading-tight">41 – 60 min</p>
                <p className="font-mono tabular-nums text-[11px] text-slate-500">{range41_60mCount} ({range41_60mPct}%)</p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="w-2.5 h-2.5 rounded-sm mt-0.5 shrink-0 bg-rose-600" />
              <div>
                <p className="font-medium text-slate-900 leading-tight">After 60 min</p>
                <p className="font-mono tabular-nums text-[11px] text-slate-500">{above60mCount} ({above60mPct}%)</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Action Link */}
      <div className="pt-3 mt-2 border-t border-slate-100 flex items-center justify-between text-xs">
        <button
          type="button"
          onClick={onOpenDetailModal}
          className="text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors flex items-center gap-1"
        >
          View dispatch accuracy details &rarr;
        </button>
      </div>
    </div>
  );
};

