import React, { useState } from 'react';

export interface QueuePoint {
  timestamp: string;
  active_queue_count: number;
}

interface QueueTrendChartProps {
  points: QueuePoint[];
  timelineData?: any;
}

export const QueueTrendChart: React.FC<QueueTrendChartProps> = ({ points, timelineData }) => {
  const [hoveredPoint, setHoveredPoint] = useState<QueuePoint | null>(null);

  if (!points || points.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-500 italic border border-slate-200 rounded-xl bg-slate-50">
        No queue trend data available for active filters.
      </div>
    );
  }

  // Derive responsive time-series points based on actual timeline dispatches if available
  let dynamicPoints = points;
  if (timelineData?.tm_timelines && timelineData.tm_timelines.length > 0) {
    const timelines = timelineData.tm_timelines;
    const timeBuckets = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"];

    dynamicPoints = timeBuckets.map((bucket) => {
      const bucketMins = parseInt(bucket.split(":")[0], 10) * 60;
      // Count TMs active (holding or unloading) during this time bucket
      const activeCount = timelines.reduce((count: number, tm: any) => {
        const parseM = (tStr: string) => {
          if (!tStr) return 0;
          const [h, m] = tStr.replace(/(AM|PM)/gi, '').trim().split(':').map(Number);
          return (h || 0) * 60 + (m || 0);
        };
        const inM = parseM(tm.site_in);
        const outM = parseM(tm.site_out);
        if (bucketMins >= inM - 30 && bucketMins <= outM + 30) {
          return count + 1;
        }
        return count;
      }, 0);

      return {
        timestamp: bucket,
        active_queue_count: Math.max(0, activeCount),
      };
    });
  }

  const maxQ = Math.max(...dynamicPoints.map((p) => p.active_queue_count), 4);
  const width = 520;
  const height = 210;
  const paddingX = 35;
  const paddingY = 40;

  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  // Handle single/sparse data points gracefully
  const coords = dynamicPoints.map((p, idx) => {
    const x = dynamicPoints.length === 1
      ? width / 2
      : paddingX + (idx / Math.max(1, dynamicPoints.length - 1)) * chartWidth;
    const y = height - paddingY - (p.active_queue_count / maxQ) * chartHeight;
    return { x, y, point: p };
  });

  // Generate SVG path string with smooth Catmull-Rom curves
  const pathD = coords.reduce((acc, curr, idx, arr) => {
    if (idx === 0) return `M ${curr.x} ${curr.y}`;
    const prev = arr[idx - 1];
    const cp1x = prev.x + (curr.x - prev.x) / 2;
    const cp1y = prev.y;
    const cp2x = prev.x + (curr.x - prev.x) / 2;
    const cp2y = curr.y;
    return `${acc} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${curr.x} ${curr.y}`;
  }, '');

  // Area under curve
  const firstX = coords[0].x;
  const lastX = coords[coords.length - 1].x;
  const bottomY = height - paddingY;
  const areaD = coords.length > 1 ? `${pathD} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z` : '';

  // Peak point for vertical red line (Unloading Started)
  const peakCoord = coords.reduce((max, c) => (c.point.active_queue_count > max.point.active_queue_count ? c : max), coords[0]);

  return (
    <div className="flex-1 min-w-0">
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-52 overflow-visible">
          <defs>
            <linearGradient id="queueCurveGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1d6bf3" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#1d6bf3" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Background Horizontal Grid Lines & Y-Axis Labels */}
          {[0, 1, 2, 3, 4, 5, 6].map((level) => {
            const y = height - paddingY - (level / maxQ) * chartHeight;
            return (
              <g key={level}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#f1f5f9"
                  strokeWidth="1"
                />
                <text x={paddingX - 8} y={y + 3} fill="#64748b" fontSize="9" fontFamily="sans-serif" fontWeight="bold" textAnchor="end">
                  {level}
                </text>
              </g>
            );
          })}

          {/* Vertical Red Dotted Line for Unloading Started at Peak */}
          {peakCoord && (
            <g>
              <line
                x1={peakCoord.x}
                y1={paddingY - 10}
                x2={peakCoord.x}
                y2={bottomY}
                stroke="#ef4444"
                strokeDasharray="2 2"
                strokeWidth="1.5"
              />
              <text x={peakCoord.x} y={paddingY - 14} fill="#ef4444" fontSize="9" fontFamily="sans-serif" fontWeight="bold" textAnchor="middle">
                Unloading Started
              </text>
            </g>
          )}

          {/* Area Fill */}
          {areaD && <path d={areaD} fill="url(#queueCurveGrad)" />}

          {/* Trend Line */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke="#1d6bf3"
              strokeWidth="2"
              strokeLinecap="round"
            />
          )}

          {/* Circular Data Points & Labels */}
          {coords.map(({ x, y, point }, idx) => (
            <g key={idx} className="cursor-pointer group" onMouseEnter={() => setHoveredPoint(point)} onMouseLeave={() => setHoveredPoint(null)}>
              {/* Value Label above node */}
              <text x={x} y={y - 8} fill="#1e293b" fontSize="10" fontFamily="sans-serif" fontWeight="bold" textAnchor="middle">
                {point.active_queue_count}
              </text>

              {/* Data Node Circle */}
              <circle
                cx={x}
                cy={y}
                r="3.5"
                fill="#1d6bf3"
                stroke="#ffffff"
                strokeWidth="1.5"
              />
              <circle cx={x} cy={y} r="10" fill="transparent" />
              
              {/* X Axis Time Labels */}
              <text x={x} y={height - 8} fill="#64748b" fontSize="9" fontFamily="mono" textAnchor="middle" fontWeight="bold">
                {point.timestamp}
              </text>
            </g>
          ))}
        </svg>

        {/* Hover Tooltip Popup */}
        {hoveredPoint && (
          <div className="absolute top-2 right-4 bg-slate-900 text-white rounded-md px-2.5 py-1 shadow-md text-[11px] font-mono flex items-center gap-2">
            <span>{hoveredPoint.timestamp}</span>
            <span className="font-bold text-blue-400">{hoveredPoint.active_queue_count} TMs</span>
          </div>
        )}
      </div>
    </div>
  );
};

