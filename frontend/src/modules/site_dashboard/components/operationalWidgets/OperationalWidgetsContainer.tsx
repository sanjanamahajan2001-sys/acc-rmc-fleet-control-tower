import React from 'react';
import { DashboardHealthWidget, DashboardHealthData } from './DashboardHealthWidget';
import { SystemReadinessWidget, SystemReadinessItem } from './SystemReadinessWidget';
import { OperationalHighlightsWidget, OperationalHighlightItem } from './OperationalHighlightsWidget';
import { OperationalEventFeed, EventItem } from './OperationalEventFeed';
import { DataQualityWidget, DataQualityItem } from './DataQualityWidget';

export interface OperationalWidgetsContainerData {
  dashboard_health: DashboardHealthData;
  readiness: SystemReadinessItem[];
  highlights: OperationalHighlightItem[];
  events: EventItem[];
  data_quality: DataQualityItem[];
}

interface OperationalWidgetsContainerProps {
  data: OperationalWidgetsContainerData | null;
  loading?: boolean;
}

export const OperationalWidgetsContainer: React.FC<OperationalWidgetsContainerProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 animate-pulse space-y-4 shadow-xl">
        <div className="h-4 w-72 bg-slate-800 rounded" />
        <div className="h-40 w-full bg-slate-800/80 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/90 space-y-6 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h2 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          SITE OPERATIONAL INTELLIGENCE WIDGETS & SYSTEM HEALTH
        </h2>
        <span className="text-[11px] font-mono text-slate-500 font-bold uppercase">Workstream 2.10 Active</span>
      </div>

      {/* 1. Dashboard Health Widget */}
      <DashboardHealthWidget health={data.dashboard_health} />

      {/* 2. System Readiness Indicators */}
      <SystemReadinessWidget readiness={data.readiness || []} />

      {/* 3. Automated Operational Highlights */}
      <OperationalHighlightsWidget highlights={data.highlights || []} />

      {/* 4. Operational Event Feed */}
      <OperationalEventFeed events={data.events || []} />

      {/* 5. Data Quality Intelligence & ERP Integrity */}
      <DataQualityWidget dataQuality={data.data_quality || []} />
    </div>
  );
};
