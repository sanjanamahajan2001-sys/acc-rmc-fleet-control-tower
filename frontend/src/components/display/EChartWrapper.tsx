import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

export interface EChartWrapperProps {
  option: EChartsOption;
  height?: string | number;
}

export const EChartWrapper: React.FC<EChartWrapperProps> = ({ option, height = 300 }) => {
  const darkThemeOption: EChartsOption = {
    backgroundColor: 'transparent',
    textStyle: {
      color: '#94A3B8',
    },
    ...option,
  };

  return <ReactECharts option={darkThemeOption} style={{ height, width: '100%' }} />;
};
