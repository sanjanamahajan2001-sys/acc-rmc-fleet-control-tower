import React, { useState } from 'react';
import { RefreshCw, AlertCircle, Info, Lock, CheckCircle2, ChevronDown, ChevronUp, Database } from 'lucide-react';
import { OperationalIntelligenceSectionConfig } from '../registry/sectionRegistry';

interface SectionRendererProps {
  config: OperationalIntelligenceSectionConfig;
  loading?: boolean;
  error?: string | null;
  calculationStatus?: 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR';
  calculationNotes?: string;
  onRetry?: () => void;
  children?: React.ReactNode;
}

export const SectionRenderer: React.FC<SectionRendererProps> = ({
  config,
  loading = false,
  error = null,
  calculationStatus = 'SUCCESS',
  calculationNotes,
  onRetry,
  children,
}) => {
  const [showLineage, setShowLineage] = useState(false);

  if (!config.enabled) {
    return null;
  }

  // Generate clean, human-readable operational domain rectangular badges
  const getSectionBadge = () => {
    switch (config.id) {
      case 'SECTION_01_OPERATIONAL_HEALTH':
        return { label: 'Live Health Index', className: 'bg-blue-50 border-blue-200 text-blue-700' };
      case 'SECTION_02_ALERTS_INTELLIGENCE':
        return { label: 'Active Exception Queue', className: 'bg-rose-50 border-rose-200 text-rose-700' };
      case 'SECTION_03_DECISION_RECOMMENDATIONS':
        return { label: 'Dispatch Directives', className: 'bg-emerald-50 border-emerald-200 text-emerald-700' };
      case 'SECTION_04_FINANCIAL_EXPOSURE':
        return { label: 'Financial Impact', className: 'bg-amber-50 border-amber-200 text-amber-700' };
      case 'SECTION_05_FLEET_EFFICIENCY':
        return { label: 'Asset Utilization', className: 'bg-blue-50 border-blue-200 text-blue-700' };
      case 'SECTION_06_COST_EXPOSURE':
        return { label: 'Cost Analysis', className: 'bg-amber-50 border-amber-200 text-amber-700' };
      default:
        return { label: 'Operational Domain', className: 'bg-slate-50 border-slate-200 text-slate-700' };
    }
  };

  const badge = getSectionBadge();

  return (
    <div className="border border-slate-200/90 rounded-lg p-5 shadow-xs space-y-4 bg-white">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="space-y-0.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h2 className="text-base sm:text-lg font-bold tracking-tight text-slate-900">
              {config.title}
            </h2>
            <span
              className={`text-[11px] font-bold px-2.5 py-0.5 rounded-md border inline-flex items-center gap-1.5 ${badge.className}`}
            >
              <CheckCircle2 className="w-3 h-3" />
              {badge.label}
            </span>
          </div>
          <p className="text-xs font-medium text-slate-500">{config.description}</p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center">
          {calculationNotes && (
            <button
              onClick={() => setShowLineage(!showLineage)}
              className="px-2.5 py-1.5 rounded-md border border-slate-200 text-[11px] font-bold flex items-center gap-1.5 transition bg-white text-slate-700 hover:bg-slate-50"
              title="Toggle Data Source and Lineage"
            >
              <Database className="w-3 h-3 text-blue-700" />
              <span className="hidden md:inline">Data Lineage</span>
              {showLineage ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}

          {onRetry && (
            <button
              onClick={onRetry}
              disabled={loading}
              className="px-3 py-1.5 rounded-md border border-slate-200 text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50 bg-white text-slate-700 hover:bg-slate-50"
              title="Refresh Section Data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-700' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          )}
        </div>
      </div>

      {/* Collapsible Lineage Drawer */}
      {showLineage && calculationNotes && (
        <div className="p-3 rounded-md border border-slate-200 bg-slate-50 text-xs font-mono flex items-start gap-2.5 text-slate-600">
          <Database className="w-4 h-4 shrink-0 mt-0.5 text-blue-700" />
          <div>
            <span className="font-bold block text-slate-900">PostgreSQL Operational Lineage:</span>
            <p className="mt-0.5 leading-relaxed">{calculationNotes}</p>
          </div>
        </div>
      )}

      {/* State 1: Loading State */}
      {loading && (
        <div className="p-8 rounded-md border border-slate-200 bg-slate-50 animate-pulse flex items-center justify-center gap-3 text-xs font-bold text-slate-600">
          <RefreshCw className="w-4 h-4 animate-spin text-blue-700" />
          <span>Synchronizing Operational Data from Live Database...</span>
        </div>
      )}

      {/* State 2: Error State */}
      {!loading && (error || calculationStatus === 'ERROR') && (
        <div className="p-4 rounded-md border border-rose-200 bg-rose-50 flex items-center justify-between text-xs font-medium text-rose-700">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error || calculationNotes || 'Unable to calculate section metrics from database authority.'}</span>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-3 py-1 border border-rose-200 rounded-md font-bold transition bg-white text-rose-700 hover:bg-rose-50"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* State 3: Not Configured / Unavailable State */}
      {!loading && !error && calculationStatus === 'NOT_CONFIGURED' && (
        <div className="p-4 rounded-md border border-amber-200 bg-amber-50 flex items-center gap-2 text-xs font-medium text-amber-700">
          <Lock className="w-4 h-4 shrink-0 text-amber-600" />
          <span>{calculationNotes || 'Not Configured / Unavailable — Required configuration rate or database parameters missing.'}</span>
        </div>
      )}

      {/* State 4: No Records State */}
      {!loading && !error && calculationStatus === 'NO_RECORDS' && (
        <div className="p-6 rounded-md border border-slate-200 bg-slate-50 text-center space-y-1 text-xs text-slate-500">
          <div className="flex justify-center text-slate-400">
            <Info className="w-5 h-5" />
          </div>
          <p className="font-bold text-slate-800">0 / No Operational Activity</p>
          <p className="text-[11px] text-slate-500">{calculationNotes || 'No canonical records match the current filter context.'}</p>
        </div>
      )}

      {/* State 5: Success State */}
      {!loading && !error && (calculationStatus === 'SUCCESS' || calculationStatus === undefined) && (
        <div>{children}</div>
      )}
    </div>
  );
};
