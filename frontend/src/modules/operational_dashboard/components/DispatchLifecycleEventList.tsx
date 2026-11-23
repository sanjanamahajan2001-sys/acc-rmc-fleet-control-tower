import React from 'react';
import { TimelineEventItem, EventAuthorityType } from '../api/timelineReplayApi';
import { CheckCircle2, Clock, AlertTriangle, HelpCircle } from 'lucide-react';

interface DispatchLifecycleEventListProps {
  events: TimelineEventItem[];
  currentStepIndex: number;
}

export const DispatchLifecycleEventList: React.FC<DispatchLifecycleEventListProps> = ({
  events,
  currentStepIndex,
}) => {
  const getBadgeStyle = (authority: EventAuthorityType, isInferred: boolean) => {
    if (isInferred || authority === 'INFERRED') {
      return {
        label: 'INFERRED ESTIMATE',
        className: 'bg-amber-900/50 text-amber-300 border-amber-700/50',
        icon: <AlertTriangle className="w-3.5 h-3.5 mr-1" />,
      };
    }
    switch (authority) {
      case 'DIRECT':
        return {
          label: 'DIRECT ERP/TELEMETRY',
          className: 'bg-emerald-900/50 text-emerald-300 border-emerald-700/50',
          icon: <CheckCircle2 className="w-3.5 h-3.5 mr-1" />,
        };
      case 'DERIVED':
        return {
          label: 'DERIVED',
          className: 'bg-blue-900/50 text-blue-300 border-blue-700/50',
          icon: <Clock className="w-3.5 h-3.5 mr-1" />,
        };
      default:
        return {
          label: 'DATA UNAVAILABLE',
          className: 'bg-slate-800 text-slate-400 border-slate-700',
          icon: <HelpCircle className="w-3.5 h-3.5 mr-1" />,
        };
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-md mb-6">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">
        Authoritative Lifecycle Journey ({events.length} Events)
      </h3>

      <div className="space-y-3">
        {events.map((evt, idx) => {
          const isPassed = idx <= currentStepIndex;
          const isCurrent = idx === currentStepIndex;
          const badge = getBadgeStyle(evt.authority_type, evt.is_inferred_estimate);

          return (
            <div
              key={`${evt.event_type}-${idx}`}
              className={`p-3.5 rounded-lg border transition-all ${
                isCurrent
                  ? 'bg-indigo-950/40 border-indigo-500 shadow-sm ring-1 ring-indigo-500/50'
                  : isPassed
                  ? 'bg-slate-800/60 border-slate-700'
                  : 'bg-slate-900/40 border-slate-800/80 opacity-50'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      isCurrent
                        ? 'bg-indigo-600 text-white'
                        : isPassed
                        ? 'bg-slate-700 text-slate-200'
                        : 'bg-slate-800 text-slate-500'
                    }`}
                  >
                    {idx + 1}
                  </div>
                  <div>
                    <div className="font-semibold text-slate-100 flex items-center gap-2">
                      {evt.event_type}
                      {evt.location_name && (
                        <span className="text-xs font-normal text-slate-400">
                          ({evt.location_name})
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {evt.timestamp ? new Date(evt.timestamp).toUTCString() : 'Timestamp Unavailable'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  {evt.duration_mins !== null && (
                    <span className="text-xs font-mono text-slate-300 bg-slate-800 px-2 py-1 rounded">
                      +{evt.duration_mins.toFixed(1)} mins
                    </span>
                  )}
                  <span
                    className={`inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded border ${badge.className}`}
                  >
                    {badge.icon}
                    {badge.label}
                  </span>
                </div>
              </div>

              {evt.notes && (
                <p className="text-xs text-slate-400 italic mt-2 pl-9 border-l-2 border-slate-700">
                  {evt.notes}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
