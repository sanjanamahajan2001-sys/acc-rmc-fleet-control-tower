import React from 'react';

export interface TimelinePhase {
  phase: 'HOLDING' | 'UNLOADING' | 'RETENTION';
  start_time: string;
  end_time: string;
  duration_mins: number;
}

export interface TMTimelineItem {
  tm_no: string;
  site_in: string;
  unloading_start: string;
  unloading_end: string;
  site_out: string;
  phases: TimelinePhase[];
}

export interface TimelineData {
  first_unloading_time: string;
  tm_timelines: TMTimelineItem[];
}

interface TMQueueTimelineGanttProps {
  data: TimelineData | null;
  loading?: boolean;
}

export const TMQueueTimelineGantt: React.FC<TMQueueTimelineGanttProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="bg-white rounded-lg border border-slate-200/90 p-4 shadow-sm animate-pulse space-y-4">
        <div className="h-4 w-48 bg-slate-200 rounded" />
        <div className="space-y-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-7 w-full bg-slate-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  // Parse time helper handling formats like "08:00", "8:00", "09:40 AM"
  const parseTimeToMins = (timeStr: string): number => {
    if (!timeStr) return 0;
    const clean = timeStr.trim();
    const isPM = clean.toUpperCase().includes('PM');
    const isAM = clean.toUpperCase().includes('AM');
    const parts = clean.replace(/(AM|PM)/gi, '').trim().split(':').map(Number);
    let hours = parts[0] || 0;
    const mins = parts[1] || 0;
    if (isPM && hours < 12) hours += 12;
    if (isAM && hours === 12) hours = 0;
    return hours * 60 + mins;
  };

  // Find min and max time across all dispatches to build dynamic time scale
  let minMins = 24 * 60;
  let maxMins = 0;

  if (data.tm_timelines && data.tm_timelines.length > 0) {
    data.tm_timelines.forEach((t) => {
      const inMins = parseTimeToMins(t.site_in);
      const outMins = parseTimeToMins(t.site_out);
      if (inMins > 0 && inMins < minMins) minMins = inMins;
      if (outMins > maxMins) maxMins = outMins;
    });
  }

  // Fallback defaults matching reference 09:00 to 11:00 if data range is invalid
  if (minMins >= maxMins || minMins === 24 * 60) {
    minMins = 9 * 60; // 09:00
    maxMins = 11 * 60; // 11:00
  } else {
    // Floor minMins to previous 10 min mark, ceil maxMins to next 10 min mark
    minMins = Math.floor(minMins / 10) * 10;
    maxMins = Math.ceil(maxMins / 10) * 10;
  }

  const totalSpanMins = Math.max(30, maxMins - minMins);

  // Generate evenly spaced tick marks (max 8 ticks) to keep time header clean and legible
  const tickMarks: { label: string; mins: number }[] = [];
  const numTicks = 8;
  const stepMins = Math.max(10, Math.ceil(totalSpanMins / (numTicks - 1) / 10) * 10);

  for (let i = 0; i < numTicks; i++) {
    const m = minMins + i * stepMins;
    if (m > maxMins + stepMins / 2) break;
    const hrs = Math.floor(m / 60) % 24;
    const mins = m % 60;
    const label = `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    tickMarks.push({ label, mins: m });
  }

  const getLeftPct = (timeStr: string) => {
    const mins = parseTimeToMins(timeStr);
    const offset = mins - minMins;
    const maxSpan = (tickMarks[tickMarks.length - 1]?.mins || maxMins) - minMins;
    return Math.max(0, Math.min(100, (offset / Math.max(1, maxSpan)) * 100));
  };

  const getWidthPct = (startTimeStr: string, endTimeStr: string) => {
    const startMins = parseTimeToMins(startTimeStr);
    const endMins = parseTimeToMins(endTimeStr);
    const duration = Math.max(0, endMins - startMins);
    const maxSpan = (tickMarks[tickMarks.length - 1]?.mins || maxMins) - minMins;
    return Math.min(100, (duration / Math.max(1, maxSpan)) * 100);
  };

  // Red dotted line position for Unloading Started
  const unloadingStartedTime = data.first_unloading_time || (tickMarks[1] ? tickMarks[1].label : '08:05');
  const unloadingLineLeftPct = getLeftPct(unloadingStartedTime);

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3">
      {/* Title & Legend Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xs font-bold uppercase tracking-tight text-slate-800">
          TM QUEUE TIMELINE <span className="font-normal text-slate-500">(GANTT VIEW)</span>
        </h2>

        {/* Legend */}
        <div className="flex items-center gap-4 text-[11px] font-medium text-slate-600">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-blue-600 rounded-xs inline-block" />
            <span>Holding (Site In → Unloading Start)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-emerald-600 rounded-xs inline-block" />
            <span>Unloading</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-orange-600 rounded-xs inline-block" />
            <span>Retention (Unload Finish → Site Out)</span>
          </div>
        </div>
      </div>

      {/* Main Gantt Grid Chart */}
      <div className="relative pt-1">
        {/* Time Scale Header */}
        <div className="flex items-center text-[11px] font-medium text-slate-600 border-b border-slate-100 pb-2">
          <div className="w-20 shrink-0 font-bold text-slate-700">
            Time →
          </div>
          <div className="flex-1 relative flex justify-between px-1 font-mono text-[11px]">
            {tickMarks.map((t) => (
              <span key={t.mins}>{t.label}</span>
            ))}
          </div>
        </div>

        {/* Scrollable Timeline Rows Container with Fixed Card Height */}
        <div className="relative my-2 space-y-2 max-h-[260px] overflow-y-auto overflow-x-hidden pr-1 border border-slate-100/80 rounded-md p-1">
          {/* Vertical Red Dotted Line for Unloading Started */}
          <div
            className="absolute top-0 bottom-0 z-20 border-r-2 border-dashed border-red-500 pointer-events-none"
            style={{ left: `calc(5rem + (100% - 5rem) * ${unloadingLineLeftPct / 100})` }}
          >
            <div className="absolute -top-4 -translate-x-1/2 text-[10px] font-bold text-red-600 bg-white px-1 whitespace-nowrap">
              Unloading Started
            </div>
          </div>

          {data.tm_timelines.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400 italic">
              No operational dispatches found for selected filter combination.
            </div>
          ) : (
            data.tm_timelines.map((item, idx) => {
              // Extract phase durations directly if timestamps are missing/identical
              const holdingPhase = item.phases?.find((p) => p.phase === 'HOLDING');
              const unloadingPhase = item.phases?.find((p) => p.phase === 'UNLOADING');
              const retentionPhase = item.phases?.find((p) => p.phase === 'RETENTION');

              const hMins = holdingPhase?.duration_mins || (parseTimeToMins(item.unloading_start) - parseTimeToMins(item.site_in)) || 10;
              const uMins = unloadingPhase?.duration_mins || (parseTimeToMins(item.unloading_end) - parseTimeToMins(item.unloading_start)) || 25;
              const rMins = retentionPhase?.duration_mins || (parseTimeToMins(item.site_out) - parseTimeToMins(item.unloading_end)) || 15;

              const totalDuration = Math.max(1, hMins + uMins + rMins);
              const holdingPct = (hMins / totalDuration) * 100;
              const unloadingPct = (uMins / totalDuration) * 100;
              const retentionPct = (rMins / totalDuration) * 100;

              const startPct = getLeftPct(item.site_in);
              const totalWidthPct = Math.max(5, getWidthPct(item.site_in, item.site_out));

              return (
                <div key={`${item.tm_no}-${idx}`} className="flex items-center h-7 text-xs font-semibold hover:bg-slate-50 rounded px-0.5 transition">
                  {/* TM Number */}
                  <div className="w-20 shrink-0 font-mono text-slate-800 text-[11px] font-bold truncate" title={item.tm_no}>
                    {item.tm_no}
                  </div>

                  {/* Gantt Bar Area */}
                  <div className="flex-1 h-full relative px-1">
                    <div
                      className="absolute h-6 top-0.5 rounded flex items-center overflow-hidden text-[10px] font-mono text-white font-bold shadow-xs"
                      style={{
                        left: `${startPct}%`,
                        width: `${totalWidthPct}%`,
                        minWidth: '120px',
                      }}
                    >
                      {/* Phase 1: Holding (Blue) */}
                      <div
                        className="h-full bg-blue-600 flex items-center justify-center border-r border-white/20 px-1 truncate shrink-0"
                        style={{ width: `${holdingPct}%` }}
                        title={`Holding: ${item.site_in} - ${item.unloading_start} (${hMins}m)`}
                      >
                        {item.site_in} - {item.unloading_start}
                      </div>

                      {/* Phase 2: Unloading (Green) */}
                      <div
                        className="h-full bg-emerald-600 flex items-center justify-center border-r border-white/20 px-1 truncate shrink-0"
                        style={{ width: `${unloadingPct}%` }}
                        title={`Unloading: ${item.unloading_start} - ${item.unloading_end} (${uMins}m)`}
                      >
                        {item.unloading_start} - {item.unloading_end}
                      </div>

                      {/* Phase 3: Retention (Orange) */}
                      <div
                        className="h-full bg-orange-600 flex items-center justify-center px-1 truncate shrink-0"
                        style={{ width: `${retentionPct}%` }}
                        title={`Retention: ${item.unloading_end} - ${item.site_out} (${rMins}m)`}
                      >
                        {item.unloading_end} - {item.site_out}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Bottom Info Banner */}
      <div className="flex items-center gap-2 text-xs text-slate-600 font-medium pt-2 border-t border-slate-100">
        <span className="w-4 h-4 rounded-full bg-blue-50 text-blue-700 border border-blue-200 flex items-center justify-center text-[10px] font-bold">i</span>
        <span>Vertical dashed marker shows initial unloading start time ({unloadingStartedTime})</span>
      </div>
    </div>
  );
};


