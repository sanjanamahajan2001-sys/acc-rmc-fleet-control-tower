import React from 'react';
import { useExecutiveKPIs } from '../hooks/useExecutiveKPIs';
import { DispatchAccuracyCard } from './DispatchAccuracyCard';
import { SiteWaitingIndexCard } from './SiteWaitingIndexCard';
import { DispatchPlanningIndexCard } from './DispatchPlanningIndexCard';
import { FleetUtilizationIndexCard } from './FleetUtilizationIndexCard';
import { TotalDispatchesCard } from './TotalDispatchesCard';
import { AlertCircle } from 'lucide-react';

export const ExecutiveKPIRibbon: React.FC = () => {
  const { kpiData, loading, error, refetchKPIs } = useExecutiveKPIs();

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-rose-300 text-xs">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400" />
          <span>{error}</span>
        </div>
        <button
          onClick={() => refetchKPIs()}
          className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 rounded-lg text-rose-200 font-semibold transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const accuracyData = kpiData?.kpis?.dispatch_accuracy;
  const swiData = kpiData?.kpis?.swi;
  const dpiData = kpiData?.kpis?.dpi;
  const fuiData = kpiData?.kpis?.fui;
  const totalDispatchesData = kpiData?.kpis?.total_dispatches;

  return (
    <div data-testid="executive-kpi-ribbon" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* Position 1. Dispatch Accuracy Card (WS-03.1 Phase 2F) */}
      {loading || !accuracyData ? (
        <DispatchAccuracyCard
          loading={true}
          data={{
            key: 'accuracy',
            label: 'Dispatch Accuracy',
            current_value: null,
            unit: '%',
            status: 'NEUTRAL' as any,
            availability: 'NO_OBSERVATIONS' as any,
          }}
        />
      ) : (
        <DispatchAccuracyCard data={accuracyData} />
      )}

      {/* Position 2. Site Waiting Index Card (WS-03.1 Phase 3F) */}
      {loading || !swiData ? (
        <SiteWaitingIndexCard
          loading={true}
          data={{
            key: 'swi',
            label: 'Site Waiting Index',
            current_value: null,
            unit: '/100',
            status: 'NEUTRAL' as any,
            availability: 'NO_OBSERVATIONS' as any,
          }}
        />
      ) : (
        <SiteWaitingIndexCard data={swiData} />
      )}

      {/* Position 3. Dispatch Planning Index Card (WS-03.1 Phase 4F) */}
      {loading || !dpiData ? (
        <DispatchPlanningIndexCard
          loading={true}
          data={{
            key: 'dpi',
            label: 'Dispatch Planning Index',
            current_value: null,
            unit: '/100',
            status: 'NEUTRAL' as any,
            availability: 'BASELINE_UNAVAILABLE' as any,
          }}
        />
      ) : (
        <DispatchPlanningIndexCard data={dpiData} />
      )}

      {/* Position 4. Fleet Utilization Index Card (WS-03.1 Phase 5F) */}
      {loading || !fuiData ? (
        <FleetUtilizationIndexCard
          loading={true}
          data={{
            key: 'fui',
            label: 'Fleet Utilization Index',
            current_value: null,
            unit: '/100',
            status: 'NEUTRAL' as any,
            availability: 'AVAILABLE' as any,
          }}
        />
      ) : (
        <FleetUtilizationIndexCard data={fuiData} />
      )}

      {/* Position 5. Total Dispatches & Volume Card (WS-03.1 Phase 6F) */}
      {loading || !totalDispatchesData ? (
        <TotalDispatchesCard
          loading={true}
          data={{
            key: 'total_dispatches',
            label: 'Total Dispatches',
            current_value: null,
            unit: 'Trips',
            status: 'NEUTRAL' as any,
            availability: 'AVAILABLE' as any,
          }}
        />
      ) : (
        <TotalDispatchesCard data={totalDispatchesData} />
      )}
    </div>
  );
};
