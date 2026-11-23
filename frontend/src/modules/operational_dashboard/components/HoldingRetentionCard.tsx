import React from 'react';
import ReactECharts from 'echarts-for-react';
import { useHoldingRetention } from '../hooks/useHoldingRetention';
import { OperationalIntelligenceStatusEnum } from '../hooks/useTopProblemCustomers';
import { IconHoldingQueueHourglass } from '../../../components/icons/LinealColorIcons';

export const HoldingRetentionCard: React.FC = () => {
  const { data, loading, error } = useHoldingRetention();

  const summary = data?.summary;
  const trendPoints = data?.data || [];
  const isNoObs = data?.status === OperationalIntelligenceStatusEnum.NO_OBSERVATIONS || summary?.total_dispatches === 0;

  // Safeguard property extraction for both DTO variations
  const holdingPenaltyMins = summary?.total_holding_penalty_mins ?? (summary as any)?.holding_penalty_mins ?? 0;
  const retentionPenaltyMins = summary?.total_retention_penalty_mins ?? (summary as any)?.retention_penalty_mins ?? 0;

  const holdingBeyondGraceHrs = (holdingPenaltyMins / 60.0).toFixed(1);
  const retentionBeyondGraceHrs = (retentionPenaltyMins / 60.0).toFixed(1);

  // Chart configuration for ECharts 2-series smooth line/area chart (Light Theme)
  const getChartOption = () => {
    const hours = trendPoints.map((p) => p.hour_label);
    const holdingMins = trendPoints.map((p) => p.holding_penalty_mins);
    const retentionMins = trendPoints.map((p) => p.retention_penalty_mins);

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        textStyle: { color: '#0f172a', fontSize: 11 },
        formatter: (params: any[]) => {
          let res = `<div style="font-weight:bold;margin-bottom:4px;color:#0f172a;">${params[0]?.name || ''}</div>`;
          params.forEach((item) => {
            const color = item.seriesName === 'Holding Time' ? '#d97706' : '#dc2626';
            res += `<div style="display:flex;justify-content:space-between;gap:12px;color:${color}; font-size:11px;">
              <span>${item.seriesName}:</span>
              <strong>${item.value}m</strong>
            </div>`;
          });
          return res;
        },
      },
      grid: {
        top: '10%',
        left: '3%',
        right: '4%',
        bottom: '12%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: hours,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b', fontSize: 9, interval: 3 },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
        axisLabel: { color: '#64748b', fontSize: 9 },
      },
      series: [
        {
          name: 'Holding Time',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: holdingMins,
          lineStyle: { width: 2, color: '#d97706' },
        },
        {
          name: 'Retention Time',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: retentionMins,
          lineStyle: { width: 2, color: '#dc2626' },
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
              <IconHoldingQueueHourglass className="w-4 h-4" />
              HOLDING &amp; RETENTION OVERVIEW
            </h3>
            <p className="text-[11px] font-normal text-slate-500 mt-0.5">Hourly Penalty Trend vs Standard Grace Limits</p>
          </div>
        </div>

        {/* Chart & Content */}
        <div className="mt-2 min-h-[190px]">
          {loading ? (
            <div className="h-44 rounded bg-slate-100 animate-pulse" />
          ) : error ? (
            <div className="py-6 text-center text-xs rounded-md p-3 font-semibold border border-rose-200 bg-rose-50 text-rose-700">
              {error}
            </div>
          ) : (
            <ReactECharts option={getChartOption()} style={{ height: '190px', width: '100%' }} />
          )}
        </div>
      </div>

      {/* Footer Metrics */}
      <div className="pt-3 mt-2 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="p-2 rounded-md border border-slate-200 bg-slate-50">
          <p className="text-[10px] font-medium uppercase text-slate-500">Grace Time</p>
          <p className="text-xs font-bold font-mono tabular-nums text-slate-900">20 min</p>
        </div>
        <div className="p-2 rounded-md border border-amber-200 bg-amber-50">
          <p className="text-[10px] font-medium uppercase text-amber-700">Holding Penalty</p>
          <p className="text-xs font-bold font-mono tabular-nums text-amber-900">
            {loading ? '...' : `${holdingBeyondGraceHrs} hrs`}
          </p>
        </div>
        <div className="p-2 rounded-md border border-rose-200 bg-rose-50">
          <p className="text-[10px] font-medium uppercase text-rose-700">Retention Penalty</p>
          <p className="text-xs font-bold font-mono tabular-nums text-rose-900">
            {loading ? '...' : `${retentionBeyondGraceHrs} hrs`}
          </p>
        </div>
      </div>
    </div>
  );
};

