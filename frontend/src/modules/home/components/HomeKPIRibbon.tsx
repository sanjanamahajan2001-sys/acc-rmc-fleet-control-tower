import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import {
  IconTransitMixer,
  IconDispatchAccuracy,
  IconHoldingHourglass,
  IconCriticalAlert,
  IconPendingAction,
} from '../../../components/icons/LinealColorIcons';

export interface HomeKPIRibbonData {
  totalDispatches: number | null;
  dispatchAccuracy: number | null;
  dispatchAccuracyTarget?: number | null;
  dispatchAccuracyVariance?: number | null;
  dispatchAccuracyStatus?: string;
  holdingBreaches: number | null;
  activeCriticalAlerts: number | null;
  pendingActions: number | null;
  loading: boolean;
}

interface HomeKPIRibbonProps {
  data: HomeKPIRibbonData;
}

export const HomeKPIRibbon: React.FC<HomeKPIRibbonProps> = ({ data }) => {
  const navigate = useNavigate();

  const cards = [
    {
      title: 'Total Dispatches',
      value: data.totalDispatches !== null ? data.totalDispatches.toLocaleString('en-IN') : '—',
      unit: 'Trips',
      subtext: 'Operational Volume',
      badge: null,
      icon: IconTransitMixer,
      accentBorder: 'border-t-blue-700',
      iconBg: 'bg-blue-50/70 border-blue-200/70',
      route: '/site-dashboard',
    },
    {
      title: 'Dispatch Accuracy',
      value: data.dispatchAccuracy !== null ? data.dispatchAccuracy.toFixed(1) + '%' : '—',
      unit: data.dispatchAccuracyTarget ? `Target: ${data.dispatchAccuracyTarget}%` : 'Target: 90%',
      subtext: 'Executive Compliance Index',
      badge:
        data.dispatchAccuracyVariance !== undefined && data.dispatchAccuracyVariance !== null ? (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
            {data.dispatchAccuracyVariance > 0 ? `+${data.dispatchAccuracyVariance}%` : `${data.dispatchAccuracyVariance}%`}
          </span>
        ) : null,
      icon: IconDispatchAccuracy,
      accentBorder: 'border-t-rose-600',
      iconBg: 'bg-rose-50/70 border-rose-200/70',
      route: '/overall-dashboard',
    },
    {
      title: 'Holding Breaches',
      value: data.holdingBreaches !== null ? data.holdingBreaches.toLocaleString('en-IN') : '—',
      unit: '> 20 min',
      subtext: 'Site Queue Breaches',
      badge: null,
      icon: IconHoldingHourglass,
      accentBorder: 'border-t-amber-500',
      iconBg: 'bg-amber-50/70 border-amber-200/70',
      route: '/dispatch-analysis',
    },
    {
      title: 'Critical Alerts',
      value: data.activeCriticalAlerts !== null ? data.activeCriticalAlerts.toLocaleString('en-IN') : '—',
      unit: 'Active',
      subtext: 'Open Incident Queue',
      badge: null,
      icon: IconCriticalAlert,
      accentBorder: 'border-t-rose-600',
      iconBg: 'bg-rose-50/70 border-rose-200/70',
      route: '/alerts',
    },
    {
      title: 'Pending Actions',
      value: data.pendingActions !== null ? data.pendingActions.toLocaleString('en-IN') : '—',
      unit: 'Pending',
      subtext: 'Control Tower Tasks',
      badge: null,
      icon: IconPendingAction,
      accentBorder: 'border-t-blue-700',
      iconBg: 'bg-blue-50/70 border-blue-200/70',
      route: '/control-tower-actions',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
      {cards.map((card, idx) => {
        const IconComp = card.icon;
        return (
          <div
            key={idx}
            onClick={() => navigate(card.route)}
            className="bg-white border border-slate-200/90 rounded-lg p-4 shadow-2xs hover:shadow-xs hover:border-slate-300 transition-all duration-150 cursor-pointer flex flex-col justify-between group"
          >
            {/* Header with Title and Icon */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold text-slate-600 group-hover:text-slate-900 transition-colors truncate">
                {card.title}
              </span>
              <div className="shrink-0 flex items-center justify-center transition-transform group-hover:scale-105">
                <IconComp className="w-5 h-5" />
              </div>
            </div>

            {/* Metric Value & Context */}
            <div className="mt-3">
              {data.loading ? (
                <div className="h-7 bg-slate-100 animate-pulse rounded w-24 my-1" />
              ) : (
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-black tracking-tight text-slate-900 font-mono tabular-nums">
                    {card.value}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">{card.unit}</span>
                  {card.badge && <div className="ml-auto">{card.badge}</div>}
                </div>
              )}
              <div className="flex items-center justify-between mt-1.5 text-[11px] text-slate-500 font-medium">
                <span className="truncate">{card.subtext}</span>
                <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-400" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
