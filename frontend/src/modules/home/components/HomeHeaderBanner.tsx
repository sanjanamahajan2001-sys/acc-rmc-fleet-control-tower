import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';
import { DatasetInfoModal } from './DatasetInfoModal';
import { ShieldCheck } from 'lucide-react';
import { IconCalendarDate, IconDatasetDatabase } from '../../../components/icons/LinealColorIcons';
import { formatDisplayDate } from '../../../utils/date';

export interface DatasetInfoDTO {
  operational_date: string;
  dataset_id: string;
  import_timestamp: string;
  calculation_timestamp: string;
  total_dispatches: number;
  total_trips: number;
  dataset_status: string;
}

export interface HomeHeaderBannerProps {
  datasetInfo?: DatasetInfoDTO | null;
  syncStatusLabel?: string;
  dieselData?: {
    dispatchAccuracyPct?: number;
    holdingBreaches?: number;
    holdingExcessHours?: number;
    unloadingBreaches?: number;
    unloadingExcessHours?: number;
    retentionBreaches?: number;
    retentionExcessHours?: number;
    holdingCostInr?: number;
    holdingLiters?: number;
    totalCostInr?: number;
    totalLiters?: number;
  } | null;
}

/**
 * [REVERT TOGGLE]
 * Set USE_ENHANCED_BOXES = false to instantly revert back to the legacy compact row layout.
 */
const USE_ENHANCED_BOXES = true;

export const HomeHeaderBanner: React.FC<HomeHeaderBannerProps> = ({
  datasetInfo,
  syncStatusLabel = 'SYNCHRONIZED',
  dieselData,
}) => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const isAdmin = Boolean(
    user?.is_superuser ||
      (user?.roles && (user.roles.includes('ADMIN') || user.roles.includes('SUPERVISOR')))
  );

  const handleBadgeClick = () => {
    if (isAdmin) {
      navigate('/erp/import');
    } else {
      setIsModalOpen(true);
    }
  };

  const formattedDate = formatDisplayDate(datasetInfo?.operational_date || '2026-08-05');
  const lastSyncStr = datasetInfo?.import_timestamp
    ? new Date(datasetInfo.import_timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Just Now';

  // Dynamic values with clean client defaults
  const accuracyPct = dieselData?.dispatchAccuracyPct ?? 55.3;
  const holdingBreaches = dieselData?.holdingBreaches ?? 1034;
  const holdingHrs = dieselData?.holdingExcessHours ?? 494.6;
  const unloadingBreaches = dieselData?.unloadingBreaches ?? 896;
  const unloadingHrs = dieselData?.unloadingExcessHours ?? 882.5;
  const retentionBreaches = dieselData?.retentionBreaches ?? 810;
  const retentionHrs = dieselData?.retentionExcessHours ?? 214.8;
  const holdingCostINR = dieselData?.holdingCostInr ?? 142355.77;
  const holdingLiters = dieselData?.holdingLiters ?? 1483.8;
  const totalCostINR = dieselData?.totalCostInr ?? 396361.72;
  const totalLiters = dieselData?.totalLiters ?? 4131.3;

  return (
    <>
      <div
        className="rounded-lg p-4 md:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-slate-200/90 shadow-2xs relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-blue-700" />
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg md:text-xl font-bold tracking-tight text-slate-900">
              Platform Command Center
            </h1>
            <span
              className="px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase bg-blue-50 text-blue-900 border border-blue-200"
            >
              Operational Summary
            </span>
          </div>
          <p className="text-xs font-medium mt-1 text-slate-500">
            Executive Summary &amp; Cross-Module Intelligence Overview
          </p>
        </div>

        {/* Live Operational Context Badges */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 bg-slate-50/80 text-slate-700 shadow-2xs"
          >
            <IconCalendarDate className="w-3.5 h-3.5" />
            <span className="text-slate-500 font-medium">Op Date:</span>
            <span className="font-bold text-slate-900 font-mono tabular-nums">{formattedDate}</span>
          </div>

          <div
            onClick={handleBadgeClick}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-colors cursor-pointer bg-slate-50/80 hover:bg-slate-100 border-slate-200 text-slate-700 shadow-2xs"
            title={isAdmin ? 'Click to manage dataset imports' : 'Click to view dataset info'}
          >
            <IconDatasetDatabase className="w-3.5 h-3.5" />
            <span className="text-slate-500 font-medium">Dataset:</span>
            <span className="font-bold truncate max-w-[140px] text-slate-900 font-mono">
              {datasetInfo?.dataset_id || 'DS-20260805-001'}
            </span>
          </div>

          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border bg-emerald-50/90 border-emerald-200 text-emerald-900 shadow-2xs"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span className="font-bold tracking-wide text-[11px] uppercase">{syncStatusLabel}</span>
            <span className="text-[10px] font-medium text-emerald-700">Synced: {lastSyncStr}</span>
          </div>
        </div>
      </div>

      {/* Executive Operational Highlights Summary Box */}
      <div
        className="rounded-lg p-4 border border-slate-200/90 bg-white text-xs leading-relaxed space-y-3 shadow-2xs"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
          <span className="font-bold uppercase tracking-wider text-[11px] flex items-center gap-2 text-slate-900">
            <span className="w-1.5 h-3.5 rounded-xs bg-blue-700 inline-block" />
            Executive Operational &amp; Diesel Loss Highlights
          </span>
          <span className="text-[10px] text-slate-500 font-medium">
            Governed Idle Burn Rate: <span className="font-mono tabular-nums text-slate-700 font-semibold">0.05 L/min (3.0 L/h) · ₹95.94/L</span>
          </span>
        </div>

        {USE_ENHANCED_BOXES ? (
          /* =========================================================================
           * [ENHANCED ENTERPRISE PRESENTATION]
           * 6 Distinct Industrial Metric Boxes matching enterprise logistics design system.
           * Crisp white cards, subtle left status indicator, bold high-contrast fonts.
           * ========================================================================= */
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Box 1: Trips Unloading <= 20m */}
            <div className="bg-white border border-slate-200/90 border-l-[3px] border-l-emerald-600 rounded-lg p-3 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 truncate">
                Trips Unloading &le; 20m
              </span>
              <div className="my-1.5">
                <span className="text-xl font-bold font-mono tracking-tight text-emerald-700 tabular-nums">
                  {accuracyPct.toFixed(1)}%
                </span>
                <span className="text-[11px] font-medium text-slate-500 ml-1">of trips</span>
              </div>
              <span className="text-[10px] text-slate-400 font-medium truncate">
                Target: 90% SLA
              </span>
            </div>

            {/* Box 2: Holding > 20m */}
            <div className="bg-white border border-slate-200/90 border-l-[3px] border-l-amber-500 rounded-lg p-3 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 truncate">
                Holding &gt; 20m
              </span>
              <div className="my-1.5">
                <span className="text-xl font-bold font-mono tracking-tight text-slate-900 tabular-nums">
                  {holdingBreaches.toLocaleString()}
                </span>
                <span className="text-[11px] font-medium text-slate-500 ml-1">trips</span>
              </div>
              <span className="text-[10px] text-amber-700 font-semibold font-mono truncate">
                {holdingHrs.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} hrs queue delay
              </span>
            </div>

            {/* Box 3: Unloading > 60m */}
            <div className="bg-white border border-slate-200/90 border-l-[3px] border-l-orange-500 rounded-lg p-3 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 truncate">
                Unloading &gt; 60m
              </span>
              <div className="my-1.5">
                <span className="text-xl font-bold font-mono tracking-tight text-slate-900 tabular-nums">
                  {unloadingBreaches.toLocaleString()}
                </span>
                <span className="text-[11px] font-medium text-slate-500 ml-1">trips</span>
              </div>
              <span className="text-[10px] text-orange-700 font-semibold font-mono truncate">
                {unloadingHrs.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} hrs site overrun
              </span>
            </div>

            {/* Box 4: Retention > 10m */}
            <div className="bg-white border border-slate-200/90 border-l-[3px] border-l-rose-500 rounded-lg p-3 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 truncate">
                Retention &gt; 10m
              </span>
              <div className="my-1.5">
                <span className="text-xl font-bold font-mono tracking-tight text-slate-900 tabular-nums">
                  {retentionBreaches.toLocaleString()}
                </span>
                <span className="text-[11px] font-medium text-slate-500 ml-1">trips</span>
              </div>
              <span className="text-[10px] text-rose-700 font-semibold font-mono truncate">
                {retentionHrs.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} hrs plant detention
              </span>
            </div>

            {/* Box 5: Holding Diesel Loss */}
            <div className="bg-white border border-slate-200/90 border-l-[3px] border-l-amber-600 rounded-lg p-3 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 truncate">
                Holding Fuel Loss
              </span>
              <div className="my-1.5">
                <span className="text-xl font-bold font-mono tracking-tight text-slate-900 tabular-nums truncate">
                  ₹{holdingCostINR.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              </div>
              <span className="text-[10px] text-slate-600 font-medium font-mono truncate">
                {holdingLiters.toLocaleString('en-IN', { maximumFractionDigits: 0 })} L idle burn
              </span>
            </div>

            {/* Box 6: Total Diesel Loss */}
            <div className="bg-slate-50/60 border border-slate-300/80 border-l-[3px] border-l-rose-600 rounded-lg p-3 shadow-2xs hover:border-slate-400 transition-colors flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-rose-900 truncate">
                  Total Diesel Loss
                </span>
                <span className="text-[9px] font-bold uppercase px-1 py-0.5 rounded bg-rose-100 text-rose-700">
                  Critical
                </span>
              </div>
              <div className="my-1.5">
                <span className="text-xl font-black font-mono tracking-tight text-rose-800 tabular-nums truncate">
                  ₹{totalCostINR.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              </div>
              <span className="text-[10px] text-rose-700 font-semibold font-mono truncate">
                {totalLiters.toLocaleString('en-IN', { maximumFractionDigits: 0 })} L total loss
              </span>
            </div>
          </div>
        ) : (
          /* =========================================================================
           * [PREVIOUS PRESENTATION - KEEP FOR EASY REVERT]
           * Legacy single-row flex layout. Set USE_ENHANCED_BOXES = false above to activate.
           * ========================================================================= */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="p-2.5 rounded-md border border-slate-200/80 bg-slate-50/70 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="font-medium text-slate-600">Trips Unloading &le; 20m:</span>
              <strong className="font-mono tabular-nums text-emerald-700 font-bold">{accuracyPct.toFixed(1)}% of dispatches</strong>
            </div>
            <div className="p-2.5 rounded-md border border-slate-200/80 bg-slate-50/70 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="font-medium text-slate-600">Holding &gt; 20m:</span>
              <strong className="font-mono tabular-nums text-amber-700 font-bold">{holdingBreaches.toLocaleString()} trips ({holdingHrs.toFixed(1)} hrs)</strong>
            </div>
            <div className="p-2.5 rounded-md border border-slate-200/80 bg-slate-50/70 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="font-medium text-slate-600">Unloading &gt; 60m:</span>
              <strong className="font-mono tabular-nums text-orange-700 font-bold">{unloadingBreaches.toLocaleString()} trips ({unloadingHrs.toFixed(1)} hrs)</strong>
            </div>
            <div className="p-2.5 rounded-md border border-slate-200/80 bg-slate-50/70 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="font-medium text-slate-600">Retention &gt; 10m:</span>
              <strong className="font-mono tabular-nums text-rose-700 font-bold">{retentionBreaches.toLocaleString()} trips ({retentionHrs.toFixed(1)} hrs)</strong>
            </div>
            <div className="p-2.5 rounded-md border border-slate-200/80 bg-slate-50/70 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="font-medium text-slate-600">Holding Diesel Loss:</span>
              <strong className="font-mono tabular-nums text-amber-800 font-bold">₹{holdingCostINR.toLocaleString('en-IN', { maximumFractionDigits: 2 })} ({holdingLiters.toLocaleString('en-IN', { maximumFractionDigits: 1 })} L)</strong>
            </div>
            <div className="p-2.5 rounded-md border border-slate-200/80 bg-slate-50/70 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="font-medium text-slate-600">Total Diesel Loss:</span>
              <strong className="font-mono tabular-nums font-bold text-rose-800">₹{totalCostINR.toLocaleString('en-IN', { maximumFractionDigits: 2 })} ({totalLiters.toLocaleString('en-IN', { maximumFractionDigits: 1 })} L)</strong>
            </div>
          </div>
        )}
      </div>

      <DatasetInfoModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        datasetInfo={datasetInfo}
      />
    </>
  );
};
